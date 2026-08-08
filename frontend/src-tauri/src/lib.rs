// Entrypoint Tauri per la versione Desktop di BikeMaster.
//
// Include:
//   - Axum server embedded su localhost (porta 8001) come backend locale
//   - SQLite (rusqlite) come database primario su disco
//   - Tauri commands per comunicazione WebView <-> Rust
//   - Endpoint REST: /health, /api/v1/rides, /api/v1/auth/me

use axum::{
    extract::{Form, Query, State as AxumState, Json as AxumJson},
    http::{HeaderMap, Method, StatusCode},
    routing::{delete, get, post, put},
    Router,
};
use bcrypt::{hash, verify, DEFAULT_COST};
use chrono::Utc;
use jsonwebtoken::{decode, encode, Algorithm, DecodingKey, EncodingKey, Header, Validation};
use rusqlite::{params, Connection, OptionalExtension};
use serde::{Deserialize, Serialize};
use std::net::SocketAddr;
use std::path::PathBuf;
use std::sync::Arc;
use std::time::{Duration, SystemTime, UNIX_EPOCH};
use tauri::State as TauriState;
use tauri::Manager;
use tauri::Emitter;
use tokio::sync::Mutex;
use tower_http::cors::CorsLayer;
use uuid::Uuid;
use futures::stream::StreamExt;

use btleplug::api::{
    BDAddr, Central, Manager as _, Peripheral as _, ScanFilter,
};
use btleplug::platform::Manager as BtleManager;

// ---- Stato condiviso del backend Axum ----

#[derive(Clone)]
struct AppState {
    db_path: PathBuf,
    conn: Arc<Mutex<Connection>>,
}

// ---- Tauri Commands (IPC WebView <-> Rust) ----

#[tauri::command]
fn get_app_info() -> serde_json::Value {
    serde_json::json!({
        "name": "Bikemaster",
        "version": env!("CARGO_PKG_VERSION"),
        "platform": std::env::consts::OS,
        "arch": std::env::consts::ARCH,
    })
}

#[tauri::command]
fn get_db_path(state: TauriState<AppState>) -> String {
    state.db_path.to_string_lossy().to_string()
}

#[derive(serde::Deserialize, Clone)]
struct BleReadArgs {
    mac_address: String,
    service_uuid: String,
    characteristic_uuid: String,
    device_type: String,
}

fn parse_sfloat(data: &[u8], offset: usize) -> Option<f64> {
    if offset + 2 > data.len() {
        return None;
    }
    let raw = u16::from_le_bytes([data[offset], data[offset + 1]]);
    let mut mantissa = (raw & 0x0fff) as i16;
    let mut exponent = ((raw >> 12) & 0x000f) as i8;
    if exponent >= 8 {
        exponent -= 16;
    }
    if mantissa >= 2048 {
        mantissa -= 4096;
    }
    Some(mantissa as f64 * 10f64.powi(exponent as i32))
}

fn parse_ble_characteristic(
    device_type: &str,
    data: &[u8],
) -> Option<(f64, String)> {
    if data.is_empty() {
        return None;
    }
    let flags = data[0];
    match device_type {
        "heart_rate" => {
            let is_uint16 = (flags & 0x01) != 0;
            let hr = if is_uint16 {
                u16::from_le_bytes([data[1], data[2]])
            } else {
                data[1] as u16
            };
            Some((hr as f64, "bpm".to_string()))
        }
        "weight_scale" => {
            let is_imperial = (flags & 0x01) != 0;
            let raw = u16::from_le_bytes([data[1], data[2]]);
            if is_imperial {
                Some((raw as f64 / 100.0, "lb".to_string()))
            } else {
                Some((raw as f64 / 200.0, "kg".to_string()))
            }
        }
        "blood_pressure" => {
            let sys = parse_sfloat(data, 1)?;
            Some((sys, "mmHg".to_string()))
        }
        "thermometer" => {
            let is_fahrenheit = (flags & 0x01) != 0;
            let temp = parse_sfloat(data, 1)?;
            if is_fahrenheit {
                let c = (temp - 32.0) * 5.0 / 9.0;
                Some((c, "°C".to_string()))
            } else {
                Some((temp, "°C".to_string()))
            }
        }
        "generic" => {
            let raw = data.get(1).copied().unwrap_or(0);
            Some((raw as f64, "value".to_string()))
        }
        _ => {
            let raw = data.get(1).copied().unwrap_or(0);
            Some((raw as f64, "value".to_string()))
        }
    }
}

#[tauri::command]
async fn ble_read_measurement(args: BleReadArgs) -> Result<serde_json::Value, String> {
    let manager = BtleManager::new()
        .await
        .map_err(|e| format!("BLE manager error: {}", e))?;
    let adapters = manager
        .adapters()
        .await
        .map_err(|e| format!("Cannot enumerate adapters: {}", e))?;
    let adapter = adapters
        .into_iter()
        .next()
        .ok_or_else(|| "No Bluetooth adapter found".to_string())?;

    let svc_uuid = uuid::Uuid::parse_str(&args.service_uuid)
        .map_err(|e| format!("Invalid service UUID: {}", e))?;
    let char_uuid = uuid::Uuid::parse_str(&args.characteristic_uuid)
        .map_err(|e| format!("Invalid characteristic UUID: {}", e))?;

    let bdaddr: BDAddr = args
        .mac_address
        .parse()
        .map_err(|e| format!("Invalid MAC address: {}", e))?;

    let scan_filter = ScanFilter {
        services: vec![svc_uuid],
        ..Default::default()
    };
    adapter
        .start_scan(scan_filter)
        .await
        .map_err(|e| format!("Scan start error: {}", e))?;

    let mut found_peripheral: Option<btleplug::platform::Peripheral> = None;
    for _ in 0..10 {
        tokio::time::sleep(Duration::from_millis(500)).await;
        let peripherals = adapter
            .peripherals()
            .await
            .map_err(|e| format!("Cannot get peripherals: {}", e))?;
        for p in peripherals {
            if p.address() == bdaddr {
                found_peripheral = Some(p);
                break;
            }
        }
        if found_peripheral.is_some() {
            break;
        }
    }
    let _ = adapter.stop_scan().await;

    let peripheral = found_peripheral
        .ok_or_else(|| "Device not found during scan. Ensure Bluetooth is on and the device is in pairing mode.".to_string())?;

    peripheral
        .connect()
        .await
        .map_err(|e| format!("Connect error: {}", e))?;

    peripheral
        .discover_services()
        .await
        .map_err(|e| format!("Discovery error: {}", e))?;

    let services = peripheral.services();
    let mut target_char: Option<btleplug::api::Characteristic> = None;
    for service in &services {
        if service.uuid == svc_uuid {
            for c in &service.characteristics {
                if c.uuid == char_uuid {
                    target_char = Some(c.clone());
                    break;
                }
            }
            break;
        }
    }

    let char = target_char
        .ok_or_else(|| "Characteristic not found on device".to_string())?;

    let value = peripheral
        .read(&char)
        .await
        .map_err(|e| format!("Read error: {}", e))?;

    let _ = peripheral.disconnect().await;

    let parsed = parse_ble_characteristic(&args.device_type, &value);
    match parsed {
        Some((val, unit)) => Ok(serde_json::json!({
            "value": val,
            "unit": unit,
            "raw": value
        })),
        None => Ok(serde_json::json!({
            "raw": value
        })),
    }
}

const HEART_RATE_SERVICE_UUID: &str = "0000180d-0000-1000-8000-00805f9b34fb";
const HEART_RATE_CHARACTERISTIC_UUID: &str = "00002a37-0000-1000-8000-00805f9b34fb";

#[derive(serde::Deserialize, Clone)]
struct HrMonitorArgs {
    mac_address: String,
    service_uuid: String,
    characteristic_uuid: String,
}

#[derive(serde::Serialize, Clone)]
struct BleDeviceInfo {
    service_uuid: String,
    characteristic_uuid: String,
    mac_address: String,
}

use std::sync::Mutex as StdMutex;

#[derive(Default)]
struct HrMonitorRegistry {
    devices: StdMutex<Vec<String>>,
}

#[tauri::command]
async fn ble_start_hr_monitoring(
    app: tauri::AppHandle,
    args: HrMonitorArgs,
) -> Result<String, String> {
    let manager = BtleManager::new()
        .await
        .map_err(|e| format!("BLE manager error: {}", e))?;
    let adapters = manager
        .adapters()
        .await
        .map_err(|e| format!("Cannot enumerate adapters: {}", e))?;
    let adapter = adapters
        .into_iter()
        .next()
        .ok_or_else(|| "No Bluetooth adapter found".to_string())?;

    let svc_uuid = uuid::Uuid::parse_str(&args.service_uuid)
        .map_err(|e| format!("Invalid service UUID: {}", e))?;
    let char_uuid = uuid::Uuid::parse_str(&args.characteristic_uuid)
        .map_err(|e| format!("Invalid characteristic UUID: {}", e))?;
    let bdaddr: BDAddr = args
        .mac_address
        .parse()
        .map_err(|e| format!("Invalid MAC address: {}", e))?;

    let scan_filter = ScanFilter {
        services: vec![svc_uuid],
        ..Default::default()
    };
    adapter
        .start_scan(scan_filter)
        .await
        .map_err(|e| format!("Scan start error: {}", e))?;

    let mut found_peripheral: Option<btleplug::platform::Peripheral> = None;
    for _ in 0..10 {
        tokio::time::sleep(Duration::from_millis(500)).await;
        let peripherals = adapter
            .peripherals()
            .await
            .map_err(|e| format!("Cannot get peripherals: {}", e))?;
        for p in peripherals {
            if p.address() == bdaddr {
                found_peripheral = Some(p);
                break;
            }
        }
        if found_peripheral.is_some() {
            break;
        }
    }
    let _ = adapter.stop_scan().await;

    let peripheral = found_peripheral
        .ok_or_else(|| "Device not found during scan. Ensure Bluetooth is on and the device is in pairing mode.".to_string())?;

    peripheral
        .connect()
        .await
        .map_err(|e| format!("Connect error: {}", e))?;

    peripheral
        .discover_services()
        .await
        .map_err(|e| format!("Discovery error: {}", e))?;

    let services = peripheral.services();
    let mut target_char: Option<btleplug::api::Characteristic> = None;
    for service in &services {
        if service.uuid == svc_uuid {
            for c in &service.characteristics {
                if c.uuid == char_uuid {
                    target_char = Some(c.clone());
                    break;
                }
            }
            break;
        }
    }

    let char = target_char
        .ok_or_else(|| "Characteristic not found on device".to_string())?;

    peripheral
        .subscribe(&char)
        .await
        .map_err(|e| format!("Subscribe error: {}", e))?;

    let notification_stream = peripheral
        .notifications()
        .await
        .map_err(|e| format!("Notifications error: {}", e))?;

    {
        let registry = app
            .try_state::<HrMonitorRegistry>()
            .ok_or("State error: HrMonitorRegistry not found")?;
        let mut devices = registry.devices.lock().unwrap();
        devices.push(args.mac_address.clone());
    }

    let app_handle = app.clone();
    let mac = args.mac_address.clone();
    tokio::spawn(async move {
        let mut notif_rx = notification_stream;
        while let Some(notif) = notif_rx.next().await {
            if let Some((hr, _unit)) = parse_ble_characteristic("heart_rate", &notif.value) {
                let payload = serde_json::json!({
                    "mac_address": mac,
                    "heart_rate": hr as i64,
                    "timestamp": chrono::Utc::now().to_rfc3339(),
                });
                app_handle.emit("hr-sample", payload).unwrap_or_else(|e| {
                    eprintln!("[HR] emit failed: {}", e);
                });
            }
        }
    });

    Ok("monitoring_started".to_string())
}

#[tauri::command]
async fn ble_get_device_info(mac_address: String) -> Result<BleDeviceInfo, String> {
    Ok(BleDeviceInfo {
        service_uuid: HEART_RATE_SERVICE_UUID.to_string(),
        characteristic_uuid: HEART_RATE_CHARACTERISTIC_UUID.to_string(),
        mac_address,
    })
}

#[tauri::command]
async fn ble_stop_hr_monitoring(app: tauri::AppHandle, mac_address: String) -> Result<String, String> {
    if let Some(registry) = app.try_state::<HrMonitorRegistry>() {
        let mut devices = registry.devices.lock().unwrap();
        devices.retain(|m| m != &mac_address);
    }
    Ok("monitoring_stopped".to_string())
}

#[tauri::command]
async fn ble_scan() -> Result<Vec<serde_json::Value>, String> {
    let manager = BtleManager::new()
        .await
        .map_err(|e| format!("BLE manager error: {}", e))?;
    let adapters = manager
        .adapters()
        .await
        .map_err(|e| format!("Cannot enumerate adapters: {}", e))?;
    let adapter = adapters
        .into_iter()
        .next()
        .ok_or_else(|| "No Bluetooth adapter found".to_string())?;

    let known_services = [
        ("0000181d-0000-1000-8000-00805f9b34fb", "weight_scale"),
        ("0000180d-0000-1000-8000-00805f9b34fb", "heart_rate"),
        ("00001810-0000-1000-8000-00805f9b34fb", "blood_pressure"),
        ("00001809-0000-1000-8000-00805f9b34fb", "thermometer"),
    ];

    let filter = ScanFilter::default();
    adapter
        .start_scan(filter)
        .await
        .map_err(|e| format!("Scan start error: {}", e))?;

    tokio::time::sleep(Duration::from_secs(5)).await;

    let peripherals = adapter
        .peripherals()
        .await
        .map_err(|e| format!("Cannot get peripherals: {}", e))?;

    let _ = adapter.stop_scan().await;

    let mut devices = Vec::new();
    for p in peripherals {
        let props = p.properties().await.map_err(|e| format!("{}", e))?;
        let (device_type, service_uuid) = props
            .as_ref()
            .and_then(|p| {
                p.services.iter().find_map(|s| {
                    let svc_uuid_str = s.to_string();
                    known_services
                        .iter()
                        .find(|(uuid, _)| *uuid == svc_uuid_str)
                        .map(|(uuid, dt)| (*dt, uuid.to_string()))
                })
            })
            .unwrap_or(("generic", "".to_string()));
        let name = props
            .as_ref()
            .and_then(|p| p.local_name.clone())
            .unwrap_or_else(|| format!("{}", p.address()));
        devices.push(serde_json::json!({
            "device_id": p.address().to_string(),
            "name": name,
            "device_type": device_type,
            "service_uuid": service_uuid,
        }));
    }
    Ok(devices)
}

#[tauri::command]
fn ble_pair(_device_id: String) -> Result<String, String> {
    Ok("paired".to_string())
}

#[tauri::command]
fn health_connect_permissions() -> Result<Vec<String>, String> {
    Ok(vec!["weight".into(), "height".into(), "heart_rate".into(), "steps".into(), "sleep".into(), "blood_pressure".into(), "activity".into()])
}

#[tauri::command]
fn health_connect_read_metrics() -> Result<serde_json::Value, String> {
    let metrics = health_connect_jni::read_metrics();
    if metrics.get("error").is_some() {
        return Ok(serde_json::json!({"weight_kg": null, "heart_rate_bpm": null, "steps": null, "error": metrics["error"].clone()}));
    }
    Ok(serde_json::json!({
        "weight_kg": metrics.get("weight_kg").cloned().and_then(|v| v.as_f64()),
        "heart_rate_bpm": metrics.get("heart_rate_bpm").cloned().and_then(|v| v.as_f64()),
        "steps": metrics.get("steps").cloned().and_then(|v| v.as_i64()),
        "sleep_hours": metrics.get("sleep_hours").cloned().and_then(|v| v.as_f64()),
        "blood_pressure_systolic": metrics.get("blood_pressure_systolic").cloned().and_then(|v| v.as_i64()),
        "activity_minutes": metrics.get("activity_minutes").cloned().and_then(|v| v.as_i64()),
    }))
}

#[tauri::command]
async fn reset_local_data(state: TauriState<'_, AppState>) -> Result<String, String> {
    let conn = state.conn.lock().await;
    conn.execute("DROP TABLE IF EXISTS rides", []).map_err(|e| e.to_string())?;
    conn.execute(
        "CREATE TABLE IF NOT EXISTS rides (
            id TEXT PRIMARY KEY,
            title TEXT NOT NULL,
            distance_m REAL NOT NULL DEFAULT 0,
            elapsed_time_s REAL NOT NULL DEFAULT 0,
            avg_speed_kmh REAL,
            elevation_gain_m REAL DEFAULT 0,
            sport_type TEXT DEFAULT 'cycling',
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            source TEXT NOT NULL DEFAULT 'manual',
            reliability_score REAL NOT NULL DEFAULT 1.0,
            sync_status TEXT NOT NULL DEFAULT 'local'
        )",
        [],
    )
    .map_err(|e| e.to_string())?;
    drop(conn);
    Ok("Dati locali resettati".to_string())
}

// Local-first app: the JWT signing secret is derived deterministically from the
// package name plus a fixed local constant. This is NOT a production secret.
// It never leaves the user's device and is only used to sign local JWTs.
const JWT_SECRET: &str = concat!(env!("CARGO_PKG_NAME"), "-local-auth-secret-bikemaster");
const JWT_EXPIRY_SECS: u64 = 60 * 60 * 24 * 30; // 30 days

#[derive(Debug, Serialize, Deserialize)]
struct Claims {
    sub: String,
    username: String,
    email: Option<String>,
    exp: usize,
}

fn now_unix() -> usize {
    SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .map(|d| d.as_secs() as usize)
        .unwrap_or(0)
}

fn sign_jwt(user_id: &str, username: &str, email: Option<&str>) -> Result<String, StatusCode> {
    let claims = Claims {
        sub: user_id.to_string(),
        username: username.to_string(),
        email: email.map(|e| e.to_string()),
        exp: now_unix() + JWT_EXPIRY_SECS as usize,
    };
    let key = EncodingKey::from_secret(JWT_SECRET.as_bytes());
    encode(&Header::new(Algorithm::HS256), &claims, &key).map_err(|_| StatusCode::INTERNAL_SERVER_ERROR)
}

fn verify_jwt(token: &str) -> Result<Claims, StatusCode> {
    let key = DecodingKey::from_secret(JWT_SECRET.as_bytes());
    let data = decode::<Claims>(token, &key, &Validation::new(Algorithm::HS256))
        .map_err(|_| StatusCode::UNAUTHORIZED)?;
    Ok(data.claims)
}

fn extract_bearer_token(headers: &HeaderMap) -> Option<String> {
    let auth = headers.get(axum::http::header::AUTHORIZATION)?;
    let auth_str = auth.to_str().ok()?;
    if auth_str.starts_with("Bearer ") {
        Some(auth_str[7..].to_string())
    } else {
        None
    }
}

async fn health_handler() -> axum::Json<serde_json::Value> {
    axum::Json(serde_json::json!({
        "status": "ok",
        "service": "bikemaster-backend",
        "timestamp": Utc::now().to_rfc3339(),
    }))
}

async fn auth_me(
    state: AxumState<AppState>,
    headers: HeaderMap,
) -> Result<axum::Json<serde_json::Value>, StatusCode> {
    let token = extract_bearer_token(&headers).ok_or(StatusCode::UNAUTHORIZED)?;
    let claims = verify_jwt(&token)?;

    let conn = state.conn.lock().await;
    let mut stmt = conn
        .prepare("SELECT id, username, email FROM users WHERE id = ?1")
        .map_err(|_| StatusCode::INTERNAL_SERVER_ERROR)?;
    let row = stmt
        .query_row(params![claims.sub], |row| {
            Ok(serde_json::json!({
                "id": row.get::<_, String>(0)?,
                "username": row.get::<_, String>(1)?,
                "email": row.get::<_, Option<String>>(2)?,
            }))
        })
        .map_err(|_| StatusCode::UNAUTHORIZED)?;

    Ok(axum::Json(row))
}

#[derive(serde::Deserialize)]
struct GoogleAuthQuery {
    redirect_uri: Option<String>,
    email: Option<String>,
    username: Option<String>,
}

async fn google_auth_handler(
    state: AxumState<AppState>,
    Query(query): Query<GoogleAuthQuery>,
) -> Result<axum::Json<serde_json::Value>, StatusCode> {
    let email = query
        .email
        .filter(|e| !e.is_empty())
        .or_else(|| query.username.clone())
        .unwrap_or_else(|| "google:anonymous".to_string());
    let username = format!("google:{}", email);
    let user_id = upsert_google_user(&state, &username, &email).await?;

    let token = sign_jwt(&user_id, &username, Some(&email))?;
    Ok(axum::Json(serde_json::json!({
        "access_token": token,
        "refresh_token": token,
        "token_type": "bearer",
        "username": username,
        "email": email,
        "id": user_id,
        "is_admin": false,
    })))
}

async fn upsert_google_user(
    state: &AppState,
    username: &str,
    email: &str,
) -> Result<String, StatusCode> {
    let conn = state.conn.lock().await;
    let now = Utc::now().to_rfc3339();

    let existing: Option<String> = conn
        .query_row(
            "SELECT id FROM users WHERE username = ?1",
            params![username],
            |row| row.get::<_, String>(0),
        )
        .ok();

    if let Some(id) = existing {
        return Ok(id);
    }

    let id = Uuid::new_v4().to_string();
    let hash = hash("$GOOGLE_OAUTH_LOCAL$", DEFAULT_COST).map_err(|_| StatusCode::INTERNAL_SERVER_ERROR)?;
    conn.execute(
        "INSERT INTO users (id, username, email, password_hash, created_at, updated_at)
         VALUES (?1, ?2, ?3, ?4, ?5, ?6)",
        params![id, username, email, hash, now, now],
    )
    .map_err(|_| StatusCode::INTERNAL_SERVER_ERROR)?;
    Ok(id)
}

#[derive(serde::Deserialize)]
struct LoginFormData {
    username: String,
    password: String,
}

async fn auth_login(
    state: AxumState<AppState>,
    Form(form): Form<LoginFormData>,
) -> Result<axum::Json<serde_json::Value>, StatusCode> {
    if form.username.is_empty() || form.password.is_empty() {
        return Err(StatusCode::BAD_REQUEST);
    }

    let conn = state.conn.lock().await;
    let row = conn
        .query_row(
            "SELECT id, username, email, password_hash FROM users WHERE username = ?1",
            params![form.username],
            |r| {
                Ok((
                    r.get::<_, String>(0)?,
                    r.get::<_, String>(1)?,
                    r.get::<_, Option<String>>(2)?,
                    r.get::<_, String>(3)?,
                ))
            },
        )
        .map_err(|_| StatusCode::UNAUTHORIZED)?;

    let (user_id, db_username, email, password_hash) = row;

    let valid = verify(&form.password, &password_hash).map_err(|_| StatusCode::INTERNAL_SERVER_ERROR)?;
    if !valid {
        return Err(StatusCode::UNAUTHORIZED);
    }

    let token = sign_jwt(&user_id, &db_username, email.as_deref())?;

    Ok(axum::Json(serde_json::json!({
        "access_token": token,
        "refresh_token": token,
        "token_type": "bearer",
        "username": db_username,
        "id": user_id,
        "is_admin": false,
    })))
}

async fn auth_register(
    state: AxumState<AppState>,
    Form(form): Form<LoginFormData>,
) -> Result<axum::Json<serde_json::Value>, StatusCode> {
    if form.username.trim().is_empty() {
        return Err(StatusCode::BAD_REQUEST);
    }
    if form.password.len() < 6 {
        return Err(StatusCode::BAD_REQUEST);
    }

    let conn = state.conn.lock().await;

    let duplicate = conn
        .query_row(
            "SELECT 1 FROM users WHERE username = ?1",
            params![form.username],
            |_| Ok(()),
        )
        .is_ok();
    if duplicate {
        return Err(StatusCode::CONFLICT);
    }

    let id = Uuid::new_v4().to_string();
    let now = Utc::now().to_rfc3339();
    let password_hash = hash(&form.password, DEFAULT_COST)
        .map_err(|_| StatusCode::INTERNAL_SERVER_ERROR)?;

    conn.execute(
        "INSERT INTO users (id, username, email, password_hash, created_at, updated_at)
         VALUES (?1, ?2, NULL, ?3, ?4, ?5)",
        params![id, form.username, password_hash, now, now],
    )
    .map_err(|_| StatusCode::INTERNAL_SERVER_ERROR)?;

    Ok(axum::Json(serde_json::json!({
        "message": "User registered successfully",
        "username": form.username,
    })))
}

// Local stateless auth: the JWT is self-contained and validated on every
// request via its signature, with no server-side session store. There is
// therefore nothing to invalidate server-side, so logout is a no-op that
// returns 200. The client discards the token locally.
async fn auth_logout(_headers: HeaderMap) -> Result<StatusCode, StatusCode> {
    Ok(StatusCode::OK)
}

async fn import_not_supported() -> Result<axum::Json<serde_json::Value>, StatusCode> {
    Err(StatusCode::NOT_IMPLEMENTED)
}

async fn list_rides(
    state: AxumState<AppState>,
) -> Result<axum::Json<serde_json::Value>, StatusCode> {
    let conn = state.conn.lock().await;
    let mut stmt = conn
        .prepare("SELECT id, title, distance_m, elapsed_time_s, avg_speed_kmh, elevation_gain_m, sport_type, created_at, updated_at, source, reliability_score, sync_status FROM rides ORDER BY created_at DESC")
        .map_err(|_| StatusCode::INTERNAL_SERVER_ERROR)?;

    let rides: Vec<serde_json::Value> = stmt
        .query_map([], |row| {
            Ok(serde_json::json!({
                "id": row.get::<_, String>(0)?,
                "title": row.get::<_, String>(1)?,
                "distance_m": row.get::<_, f64>(2)?,
                "elapsed_time_s": row.get::<_, f64>(3)?,
                "avg_speed_kmh": row.get::<_, Option<f64>>(4)?,
                "elevation_gain_m": row.get::<_, f64>(5)?,
                "sport_type": row.get::<_, String>(6)?,
                "created_at": row.get::<_, String>(7)?,
                "updated_at": row.get::<_, String>(8)?,
                "source": row.get::<_, String>(9)?,
                "reliability_score": row.get::<_, f64>(10)?,
                "sync_status": row.get::<_, String>(11)?,
            }))
        })
        .map_err(|_| StatusCode::INTERNAL_SERVER_ERROR)?
        .collect::<Result<Vec<_>, _>>()
        .map_err(|_| StatusCode::INTERNAL_SERVER_ERROR)?;

    Ok(axum::Json(serde_json::json!({ "rides": rides })))
}

async fn create_ride(
    state: AxumState<AppState>,
    axum::Json(payload): axum::Json<serde_json::Value>,
) -> Result<axum::Json<serde_json::Value>, StatusCode> {
    let id = Uuid::new_v4().to_string();
    let now = Utc::now().to_rfc3339();
    let title = payload
        .get("title")
        .and_then(|v| v.as_str())
        .unwrap_or("Untitled")
        .to_string();
    let distance_m = payload
        .get("distance_m")
        .and_then(|v| v.as_f64())
        .unwrap_or(0.0);
    let elapsed_time_s = payload
        .get("elapsed_time_s")
        .and_then(|v| v.as_f64())
        .unwrap_or(0.0);
    let avg_speed_kmh = payload.get("avg_speed_kmh").and_then(|v| v.as_f64());
    let elevation_gain_m = payload
        .get("elevation_gain_m")
        .and_then(|v| v.as_f64())
        .unwrap_or(0.0);
    let sport_type = payload
        .get("sport_type")
        .and_then(|v| v.as_str())
        .unwrap_or("cycling")
        .to_string();

    let conn = state.conn.lock().await;
    conn.execute(
        "INSERT INTO rides (id, title, distance_m, elapsed_time_s, avg_speed_kmh, elevation_gain_m, sport_type, created_at, updated_at, source, reliability_score, sync_status)
         VALUES (?1, ?2, ?3, ?4, ?5, ?6, ?7, ?8, ?9, 'manual', 1.0, 'local')",
        params![id, title, distance_m, elapsed_time_s, avg_speed_kmh, elevation_gain_m, sport_type, now, now],
    )
    .map_err(|_| StatusCode::INTERNAL_SERVER_ERROR)?;

    Ok(axum::Json(serde_json::json!({ "id": id, "created_at": now })))
}

async fn get_ride(
    state: AxumState<AppState>,
    axum::extract::Path(id): axum::extract::Path<String>,
) -> Result<axum::Json<serde_json::Value>, StatusCode> {
    let conn = state.conn.lock().await;
    let mut stmt = conn
        .prepare("SELECT id, title, distance_m, elapsed_time_s, avg_speed_kmh, elevation_gain_m, sport_type, created_at, updated_at, source, reliability_score, sync_status FROM rides WHERE id = ?1")
        .map_err(|_| StatusCode::INTERNAL_SERVER_ERROR)?;

    let result = stmt
        .query_row(params![id], |row| {
            Ok(serde_json::json!({
                "id": row.get::<_, String>(0)?,
                "title": row.get::<_, String>(1)?,
                "distance_m": row.get::<_, f64>(2)?,
                "elapsed_time_s": row.get::<_, f64>(3)?,
                "avg_speed_kmh": row.get::<_, Option<f64>>(4)?,
                "elevation_gain_m": row.get::<_, f64>(5)?,
                "sport_type": row.get::<_, String>(6)?,
                "created_at": row.get::<_, String>(7)?,
                "updated_at": row.get::<_, String>(8)?,
                "source": row.get::<_, String>(9)?,
                "reliability_score": row.get::<_, f64>(10)?,
                "sync_status": row.get::<_, String>(11)?,
            }))
        })
        .map_err(|_| StatusCode::NOT_FOUND)?;

    Ok(axum::Json(result))
}

// ---- Offline-first sync layer ----

fn get_sync_mode(conn: &Connection) -> String {
    conn.query_row(
        "SELECT value FROM sync_meta WHERE key = 'sync_mode'",
        [],
        |row| row.get::<_, String>(0),
    )
    .unwrap_or_else(|_| "local".to_string())
}

fn set_sync_mode(conn: &Connection, mode: &str) -> Result<(), StatusCode> {
    conn.execute(
        "INSERT INTO sync_meta (key, value) VALUES ('sync_mode', ?1)
         ON CONFLICT(key) DO UPDATE SET value = ?1",
        params![mode],
    )
    .map_err(|_| StatusCode::INTERNAL_SERVER_ERROR)?;
    Ok(())
}

async fn sync_status_handler(
    state: AxumState<AppState>,
) -> Result<axum::Json<serde_json::Value>, StatusCode> {
    let conn = state.conn.lock().await;
    let mode = get_sync_mode(&conn);
    let pending_count: i64 = conn
        .query_row(
            "SELECT COUNT(*) FROM sync_queue WHERE status = 'pending'",
            [],
            |row| row.get::<_, i64>(0),
        )
        .map_err(|_| StatusCode::INTERNAL_SERVER_ERROR)?;
    let last_sync_at: Option<String> = conn
        .query_row(
            "SELECT value FROM sync_meta WHERE key = 'last_sync_at'",
            [],
            |row| row.get::<_, String>(0),
        )
        .ok();
    Ok(axum::Json(serde_json::json!({
        "mode": mode,
        "last_sync_at": last_sync_at,
        "pending_count": pending_count,
    })))
}

async fn sync_settings_handler(
    state: AxumState<AppState>,
    axum::Json(payload): axum::Json<serde_json::Value>,
) -> Result<axum::Json<serde_json::Value>, StatusCode> {
    let mode = payload
        .get("mode")
        .and_then(|v| v.as_str())
        .unwrap_or("local");
    if mode != "local" && mode != "cloud" {
        return Err(StatusCode::BAD_REQUEST);
    }
    let conn = state.conn.lock().await;
    set_sync_mode(&conn, mode)?;
    Ok(axum::Json(serde_json::json!({ "ok": true })))
}

async fn sync_export_handler(
    state: AxumState<AppState>,
) -> Result<axum::Json<serde_json::Value>, StatusCode> {
    let conn = state.conn.lock().await;

    let last_sync_at: Option<String> = conn
        .query_row(
            "SELECT value FROM sync_meta WHERE key = 'last_sync_at'",
            [],
            |row| row.get::<_, String>(0),
        )
        .ok();

    let mut rides_stmt = conn
        .prepare("SELECT id, title, distance_m, elapsed_time_s, avg_speed_kmh, elevation_gain_m, sport_type, created_at, updated_at, source, reliability_score, sync_status, remote_id FROM rides ORDER BY created_at DESC")
        .map_err(|_| StatusCode::INTERNAL_SERVER_ERROR)?;
    let rides: Vec<serde_json::Value> = rides_stmt
        .query_map([], |row| {
            Ok(serde_json::json!({
                "id": row.get::<_, String>(0)?,
                "title": row.get::<_, String>(1)?,
                "distance_m": row.get::<_, f64>(2)?,
                "elapsed_time_s": row.get::<_, f64>(3)?,
                "avg_speed_kmh": row.get::<_, Option<f64>>(4)?,
                "elevation_gain_m": row.get::<_, f64>(5)?,
                "sport_type": row.get::<_, String>(6)?,
                "created_at": row.get::<_, String>(7)?,
                "updated_at": row.get::<_, String>(8)?,
                "source": row.get::<_, String>(9)?,
                "reliability_score": row.get::<_, f64>(10)?,
                "sync_status": row.get::<_, String>(11)?,
                "remote_id": row.get::<_, Option<String>>(12)?,
            }))
        })
        .map_err(|_| StatusCode::INTERNAL_SERVER_ERROR)?
        .collect::<Result<Vec<_>, _>>()
        .map_err(|_| StatusCode::INTERNAL_SERVER_ERROR)?;

    let mut queue_stmt = conn
        .prepare("SELECT id, entity, entity_id, operation, payload, created_at, status FROM sync_queue ORDER BY created_at DESC")
        .map_err(|_| StatusCode::INTERNAL_SERVER_ERROR)?;
    let queue: Vec<serde_json::Value> = queue_stmt
        .query_map([], |row| {
            Ok(serde_json::json!({
                "id": row.get::<_, String>(0)?,
                "entity": row.get::<_, String>(1)?,
                "entity_id": row.get::<_, String>(2)?,
                "operation": row.get::<_, String>(3)?,
                "payload": row.get::<_, String>(4)?,
                "created_at": row.get::<_, String>(5)?,
                "status": row.get::<_, String>(6)?,
            }))
        })
        .map_err(|_| StatusCode::INTERNAL_SERVER_ERROR)?
        .collect::<Result<Vec<_>, _>>()
        .map_err(|_| StatusCode::INTERNAL_SERVER_ERROR)?;

    Ok(axum::Json(serde_json::json!({
        "last_sync_at": last_sync_at,
        "rides": rides,
        "queue": queue,
    })))
}

async fn sync_import_handler(
    state: AxumState<AppState>,
    axum::Json(payload): axum::Json<serde_json::Value>,
) -> Result<axum::Json<serde_json::Value>, StatusCode> {
    let rides = payload
        .get("rides")
        .and_then(|v| v.as_array())
        .cloned()
        .unwrap_or_default();

    let now = chrono::Utc::now().to_rfc3339();
    let conn = state.conn.lock().await;
    let mut imported = 0i64;

    for ride in &rides {
        let id = match ride.get("id").and_then(|v| v.as_str()) {
            Some(id) => id.to_string(),
            None => continue,
        };
        let title = ride
            .get("title")
            .and_then(|v| v.as_str())
            .unwrap_or("Untitled")
            .to_string();
        let distance_m = ride.get("distance_m").and_then(|v| v.as_f64()).unwrap_or(0.0);
        let elapsed_time_s = ride
            .get("elapsed_time_s")
            .and_then(|v| v.as_f64())
            .unwrap_or(0.0);
        let avg_speed_kmh = ride.get("avg_speed_kmh").and_then(|v| v.as_f64());
        let elevation_gain_m = ride
            .get("elevation_gain_m")
            .and_then(|v| v.as_f64())
            .unwrap_or(0.0);
        let sport_type = ride
            .get("sport_type")
            .and_then(|v| v.as_str())
            .unwrap_or("cycling")
            .to_string();
        let created_at = ride
            .get("created_at")
            .and_then(|v| v.as_str())
            .unwrap_or(&now)
            .to_string();
        let updated_at = ride
            .get("updated_at")
            .and_then(|v| v.as_str())
            .unwrap_or(&now)
            .to_string();
        let source = ride
            .get("source")
            .and_then(|v| v.as_str())
            .unwrap_or("manual")
            .to_string();
        let reliability_score = ride
            .get("reliability_score")
            .and_then(|v| v.as_f64())
            .unwrap_or(1.0);

        conn.execute(
            "INSERT INTO rides (id, title, distance_m, elapsed_time_s, avg_speed_kmh, elevation_gain_m, sport_type, created_at, updated_at, source, reliability_score, sync_status, remote_id)
             VALUES (?1, ?2, ?3, ?4, ?5, ?6, ?7, ?8, ?9, ?10, ?11, 'synced', ?1)
             ON CONFLICT(id) DO UPDATE SET
                title = ?2,
                distance_m = ?3,
                elapsed_time_s = ?4,
                avg_speed_kmh = ?5,
                elevation_gain_m = ?6,
                sport_type = ?7,
                created_at = ?8,
                updated_at = ?9,
                source = ?10,
                reliability_score = ?11,
                sync_status = 'synced',
                remote_id = ?1",
            params![
                id,
                title,
                distance_m,
                elapsed_time_s,
                avg_speed_kmh,
                elevation_gain_m,
                sport_type,
                created_at,
                updated_at,
                source,
                reliability_score
            ],
        )
        .map_err(|_| StatusCode::INTERNAL_SERVER_ERROR)?;
        imported += 1;
    }

    Ok(axum::Json(serde_json::json!({ "ok": true, "imported": imported })))
}

// ---- SQLite init ----

fn init_db(db_path: &std::path::Path) -> Result<Connection, rusqlite::Error> {
    if let Some(parent) = db_path.parent() {
        std::fs::create_dir_all(parent).map_err(|_e| {
            rusqlite::Error::InvalidPath(db_path.to_path_buf())
        })?;
    }
    let conn = Connection::open(db_path)?;
    conn.execute_batch(
        "PRAGMA journal_mode = WAL;
         PRAGMA foreign_keys = ON;
         CREATE TABLE IF NOT EXISTS rides (
            id TEXT PRIMARY KEY,
            title TEXT NOT NULL,
            distance_m REAL NOT NULL DEFAULT 0,
            elapsed_time_s REAL NOT NULL DEFAULT 0,
            avg_speed_kmh REAL,
            elevation_gain_m REAL DEFAULT 0,
            sport_type TEXT DEFAULT 'cycling',
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            source TEXT NOT NULL DEFAULT 'manual',
            reliability_score REAL NOT NULL DEFAULT 1.0,
            sync_status TEXT NOT NULL DEFAULT 'local'
         );
         CREATE TABLE IF NOT EXISTS athlete (
            id TEXT PRIMARY KEY CHECK (id = 'default'),
            data TEXT NOT NULL
         );
         CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL
         );
         CREATE TABLE IF NOT EXISTS users (
            id TEXT PRIMARY KEY,
            username TEXT UNIQUE NOT NULL,
            email TEXT,
            password_hash TEXT NOT NULL,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
         );
         CREATE TABLE IF NOT EXISTS sync_queue (
            id TEXT PRIMARY KEY,
            entity TEXT NOT NULL,
            entity_id TEXT NOT NULL,
            operation TEXT NOT NULL,
            payload TEXT NOT NULL,
            created_at TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'pending'
         );
          CREATE TABLE IF NOT EXISTS sync_meta (
             key TEXT PRIMARY KEY,
             value TEXT NOT NULL
          );
          CREATE TABLE IF NOT EXISTS ble_devices (
             id INTEGER PRIMARY KEY AUTOINCREMENT,
             athlete_id INTEGER NOT NULL,
             tenant_id INTEGER NOT NULL DEFAULT 0,
             device_id TEXT NOT NULL,
             name TEXT NOT NULL,
             device_type TEXT NOT NULL DEFAULT 'weight_scale',
             service_uuid TEXT,
             characteristic_uuid TEXT,
             mac_address TEXT,
             paired INTEGER NOT NULL DEFAULT 1,
             last_connected_at TEXT,
             last_synced_at TEXT,
             settings TEXT NOT NULL DEFAULT '{}',
             created_at TEXT,
             updated_at TEXT
          );
          CREATE UNIQUE INDEX IF NOT EXISTS uq_ble_device ON ble_devices(athlete_id, device_id);
           CREATE TABLE IF NOT EXISTS athlete_metric_log (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              athlete_id INTEGER NOT NULL,
              tenant_id INTEGER NOT NULL DEFAULT 0,
              metric_type TEXT NOT NULL,
              value REAL,
              unit TEXT,
              note TEXT,
              source TEXT NOT NULL DEFAULT 'manual',
              recorded_at TEXT,
              created_at TEXT
           );
           CREATE TABLE IF NOT EXISTS health_connect_tokens (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              athlete_id INTEGER NOT NULL UNIQUE,
              connected INTEGER NOT NULL DEFAULT 1,
              permissions TEXT DEFAULT '[]',
              last_sync_at TEXT,
              created_at TEXT DEFAULT (datetime('now')),
              updated_at TEXT DEFAULT (datetime('now'))
           );
           CREATE TABLE IF NOT EXISTS hr_24h_samples (
             id INTEGER PRIMARY KEY AUTOINCREMENT,
             athlete_id INTEGER NOT NULL,
             tenant_id INTEGER NOT NULL DEFAULT 0,
             heart_rate INTEGER NOT NULL,
             source TEXT NOT NULL DEFAULT 'ble',
             device_id TEXT,
             recorded_at TEXT NOT NULL,
             created_at TEXT
          );
          CREATE INDEX IF NOT EXISTS idx_hr_samples_athlete_recorded ON hr_24h_samples(athlete_id, recorded_at);
          CREATE TABLE IF NOT EXISTS hr_monitoring_settings (
             id INTEGER PRIMARY KEY AUTOINCREMENT,
             athlete_id INTEGER NOT NULL,
             tenant_id INTEGER NOT NULL DEFAULT 0,
             enabled INTEGER NOT NULL DEFAULT 1,
             interval_seconds INTEGER NOT NULL DEFAULT 30,
             source TEXT NOT NULL DEFAULT 'ble',
             device_id TEXT,
             max_hr INTEGER,
             resting_hr INTEGER,
             created_at TEXT,
             updated_at TEXT,
             UNIQUE(athlete_id)
          );",
    )?;

    let has_remote_id: bool = conn
        .prepare("PRAGMA table_info(rides)")
        .map_err(|e| e)?
        .query_map([], |row| {
            Ok(row.get::<_, String>(1)?)
        })
        .map_err(|e| e)?
        .any(|c| c.map(|name| name == "remote_id").unwrap_or(false));
    if !has_remote_id {
        conn.execute("ALTER TABLE rides ADD COLUMN remote_id TEXT", [])
            .map_err(|e| e)?;
    }

    Ok(conn)
}

// ---- BLE device management (desktop fallback / metadata) ----

#[derive(serde::Deserialize)]
struct BleDeviceRegister {
    device_id: String,
    name: String,
    device_type: String,
    service_uuid: Option<String>,
    characteristic_uuid: Option<String>,
    mac_address: Option<String>,
}

#[derive(serde::Deserialize)]
struct BleDeviceUpdate {
    name: Option<String>,
    paired: Option<bool>,
    settings: Option<String>,
}

#[derive(serde::Deserialize)]
struct BleSyncPayload {
    value: Option<f64>,
    unit: Option<String>,
    recorded_at: Option<String>,
}

#[derive(serde::Serialize)]
struct BleDeviceOut {
    id: i32,
    athlete_id: i32,
    tenant_id: i32,
    device_id: String,
    name: String,
    device_type: String,
    service_uuid: Option<String>,
    characteristic_uuid: Option<String>,
    mac_address: Option<String>,
    paired: bool,
    last_connected_at: Option<String>,
    last_synced_at: Option<String>,
    settings: String,
    created_at: Option<String>,
    updated_at: Option<String>,
}

async fn ble_list_devices(
    state: AxumState<AppState>,
    headers: HeaderMap,
) -> Result<axum::Json<serde_json::Value>, StatusCode> {
    let token = extract_bearer_token(&headers).ok_or(StatusCode::UNAUTHORIZED)?;
    let claims = verify_jwt(&token)?;
    let conn = state.conn.lock().await;
    let mut stmt = conn.prepare(
        "SELECT id, athlete_id, tenant_id, device_id, name, device_type, service_uuid, characteristic_uuid, mac_address, paired, last_connected_at, last_synced_at, settings, created_at, updated_at FROM ble_devices WHERE athlete_id = ?1 ORDER BY created_at DESC",
    ).map_err(|_| StatusCode::INTERNAL_SERVER_ERROR)?;
    let athlete_id: i32 = claims.sub.parse().map_err(|_| StatusCode::UNAUTHORIZED)?;
    let rows = stmt.query_map(params![athlete_id], |row| {
        Ok(BleDeviceOut {
            id: row.get(0)?,
            athlete_id: row.get(1)?,
            tenant_id: row.get(2)?,
            device_id: row.get(3)?,
            name: row.get(4)?,
            device_type: row.get(5)?,
            service_uuid: row.get(6)?,
            characteristic_uuid: row.get(7)?,
            mac_address: row.get(8)?,
            paired: row.get(9)?,
            last_connected_at: row.get(10)?,
            last_synced_at: row.get(11)?,
            settings: row.get(12)?,
            created_at: row.get(13)?,
            updated_at: row.get(14)?,
        })
    }).map_err(|_| StatusCode::INTERNAL_SERVER_ERROR)?
    .collect::<Result<Vec<_>, _>>().map_err(|_| StatusCode::INTERNAL_SERVER_ERROR)?;
    Ok(axum::Json(serde_json::json!({ "devices": rows })))
}

async fn ble_register_device(
    state: AxumState<AppState>,
    headers: HeaderMap,
    axum::Json(payload): axum::Json<BleDeviceRegister>,
) -> Result<axum::Json<serde_json::Value>, StatusCode> {
    let token = extract_bearer_token(&headers).ok_or(StatusCode::UNAUTHORIZED)?;
    let claims = verify_jwt(&token)?;
    let athlete_id: i32 = claims.sub.parse().map_err(|_| StatusCode::UNAUTHORIZED)?;
    let now = Utc::now().to_rfc3339();
    let conn = state.conn.lock().await;
    conn.execute(
        "INSERT INTO ble_devices (athlete_id, tenant_id, device_id, name, device_type, service_uuid, characteristic_uuid, mac_address, paired, settings, created_at, updated_at) VALUES (?1, ?2, ?3, ?4, ?5, ?6, ?7, ?8, 1, '{}', ?9, ?9) ON CONFLICT(athlete_id, device_id) DO UPDATE SET name=excluded.name, device_type=excluded.device_type, service_uuid=excluded.service_uuid, characteristic_uuid=excluded.characteristic_uuid, mac_address=excluded.mac_address, paired=1, updated_at=excluded.updated_at",
        params![athlete_id, athlete_id, payload.device_id, payload.name, payload.device_type, payload.service_uuid, payload.characteristic_uuid, payload.mac_address, now],
    ).map_err(|_| StatusCode::INTERNAL_SERVER_ERROR)?;
    Ok(axum::Json(serde_json::json!({ "id": payload.device_id, "device_id": payload.device_id, "name": payload.name })))
}

async fn ble_update_device(
    state: AxumState<AppState>,
    headers: HeaderMap,
    axum::extract::Path(id): axum::extract::Path<i32>,
    axum::Json(payload): axum::Json<BleDeviceUpdate>,
) -> Result<axum::Json<serde_json::Value>, StatusCode> {
    let token = extract_bearer_token(&headers).ok_or(StatusCode::UNAUTHORIZED)?;
    let claims = verify_jwt(&token)?;
    let athlete_id: i32 = claims.sub.parse().map_err(|_| StatusCode::UNAUTHORIZED)?;
    let conn = state.conn.lock().await;
    let mut set_parts = Vec::new();
    let mut values: Vec<String> = Vec::new();
    if let Some(name) = payload.name { set_parts.push("name = ?"); values.push(name); }
    if let Some(paired) = payload.paired { set_parts.push("paired = ?"); values.push(if paired { "1" } else { "0" }.to_string()); }
    if let Some(settings) = payload.settings { set_parts.push("settings = ?"); values.push(settings); }
    if set_parts.is_empty() {
        return Ok(axum::Json(serde_json::json!({"updated": false})));
    }
    let now = Utc::now().to_rfc3339();
    set_parts.push("updated_at = ?");
    values.push(now);
    values.extend_from_slice(&[id.to_string(), athlete_id.to_string()]);
    let sql = format!("UPDATE ble_devices SET {} WHERE id = ? AND athlete_id = ?", set_parts.join(", "));
    conn.execute(&sql, rusqlite::params_from_iter(values)).map_err(|_| StatusCode::INTERNAL_SERVER_ERROR)?;
    Ok(axum::Json(serde_json::json!({"updated": true})))
}

async fn ble_delete_device(
    state: AxumState<AppState>,
    headers: HeaderMap,
    axum::extract::Path(id): axum::extract::Path<i32>,
) -> Result<axum::Json<serde_json::Value>, StatusCode> {
    let token = extract_bearer_token(&headers).ok_or(StatusCode::UNAUTHORIZED)?;
    let claims = verify_jwt(&token)?;
    let athlete_id: i32 = claims.sub.parse().map_err(|_| StatusCode::UNAUTHORIZED)?;
    let conn = state.conn.lock().await;
    conn.execute("DELETE FROM ble_devices WHERE id = ? AND athlete_id = ?", params![id, athlete_id])
        .map_err(|_| StatusCode::INTERNAL_SERVER_ERROR)?;
    Ok(axum::Json(serde_json::json!({"status": "deleted", "id": id})))
}

async fn ble_sync_device(
    state: AxumState<AppState>,
    headers: HeaderMap,
    axum::extract::Path(id): axum::extract::Path<i32>,
    AxumJson(payload): AxumJson<BleSyncPayload>,
) -> Result<axum::Json<serde_json::Value>, StatusCode> {
    let token = extract_bearer_token(&headers).ok_or(StatusCode::UNAUTHORIZED)?;
    let claims = verify_jwt(&token)?;
    let athlete_id: i32 = claims.sub.parse().map_err(|_| StatusCode::UNAUTHORIZED)?;
    let tenant_id: i32 = claims.sub.parse().map_err(|_| StatusCode::UNAUTHORIZED)?;
    let now = Utc::now().to_rfc3339();
    let conn = state.conn.lock().await;

    let row = conn
        .query_row(
            "SELECT device_type, device_id FROM ble_devices WHERE id = ? AND athlete_id = ?",
            params![id, athlete_id],
            |r| Ok((r.get::<_, String>(0)?, r.get::<_, String>(1)?)),
        )
        .map_err(|_| StatusCode::NOT_FOUND)?;
    let (device_type, device_db_id) = row;

    let mut metric_id: i64 = 0;
    if let Some(value) = payload.value {
        let metric_type = match device_type.as_str() {
            "weight_scale" => if payload.unit.as_deref() == Some("lb") { "weight_lb" } else { "weight_kg" },
            "heart_rate" => "heart_rate_bpm",
            "blood_pressure" => "blood_pressure_systolic",
            "thermometer" => "temperature_c",
            _ => "ble_generic",
        };
        conn.execute(
            "INSERT INTO athlete_metric_log (athlete_id, tenant_id, metric_type, value, unit, note, source, recorded_at, created_at) VALUES (?1, ?2, ?3, ?4, ?5, ?6, 'ble', ?7, ?8)",
            params![athlete_id, tenant_id, metric_type, value, payload.unit, format!("ble:{}", device_db_id), payload.recorded_at.as_deref().unwrap_or(&now), now],
        ).map_err(|_| StatusCode::INTERNAL_SERVER_ERROR)?;
        metric_id = conn.last_insert_rowid();
    }
    conn.execute("UPDATE ble_devices SET last_synced_at = ? WHERE id = ? AND athlete_id = ?", params![now, id, athlete_id])
        .map_err(|_| StatusCode::INTERNAL_SERVER_ERROR)?;
    Ok(axum::Json(serde_json::json!({
        "status": "synced",
        "device_id": id,
        "type": device_type,
        "metric_id": metric_id,
    })))
}

// ---- Health Connect (Android) ----

async fn list_import_providers() -> axum::Json<serde_json::Value> {
    axum::Json(serde_json::json!({
        "google_fit": false,
        "google_health": false,
        "wahoo": false,
        "strava": false,
        "ble": true,
        "health_connect": true,
        "hr_24h": true,
    }))
}

async fn health_connect_status(
    state: AxumState<AppState>,
    headers: HeaderMap,
) -> Result<axum::Json<serde_json::Value>, StatusCode> {
    let token = extract_bearer_token(&headers).ok_or(StatusCode::UNAUTHORIZED)?;
    let claims = verify_jwt(&token)?;
    Ok(axum::Json(serde_json::json!({
        "available": true,
        "connected": false,
        "permissions": [],
        "athlete_id": claims.sub,
    })))
}

async fn health_connect_connect(
    state: AxumState<AppState>,
    headers: HeaderMap,
) -> Result<axum::Json<serde_json::Value>, StatusCode> {
    let token = extract_bearer_token(&headers).ok_or(StatusCode::UNAUTHORIZED)?;
    let claims = verify_jwt(&token)?;
    let athlete_id: i32 = claims.sub.parse().map_err(|_| StatusCode::UNAUTHORIZED)?;
    let conn = state.conn.lock().await;
    let now = Utc::now().to_rfc3339();
    conn.execute(
        "INSERT INTO health_connect_tokens (athlete_id, connected, permissions, created_at, updated_at) VALUES (?1, 1, ?2, ?3, ?3) ON CONFLICT(athlete_id) DO UPDATE SET connected = 1, permissions = excluded.permissions, updated_at = excluded.updated_at",
        params![athlete_id, "[\"weight\",\"heart_rate\",\"steps\",\"sleep\",\"blood_pressure\",\"activity\"]", now],
    ).map_err(|_| StatusCode::INTERNAL_SERVER_ERROR)?;
    Ok(axum::Json(serde_json::json!({
        "status": "connected",
        "permissions": ["weight", "height", "heart_rate", "steps", "sleep", "blood_pressure", "activity"],
    })))
}

async fn health_connect_disconnect(
    state: AxumState<AppState>,
    headers: HeaderMap,
) -> Result<axum::Json<serde_json::Value>, StatusCode> {
    let token = extract_bearer_token(&headers).ok_or(StatusCode::UNAUTHORIZED)?;
    let claims = verify_jwt(&token)?;
    let athlete_id: i32 = claims.sub.parse().map_err(|_| StatusCode::UNAUTHORIZED)?;
    let conn = state.conn.lock().await;
    conn.execute(
        "DELETE FROM health_connect_tokens WHERE athlete_id = ?1",
        params![athlete_id],
    ).map_err(|_| StatusCode::INTERNAL_SERVER_ERROR)?;
    Ok(axum::Json(serde_json::json!({"status": "disconnected"})))
}

async fn health_connect_sync(
    state: AxumState<AppState>,
    headers: HeaderMap,
    axum::Json(payload): axum::Json<serde_json::Value>,
) -> Result<axum::Json<serde_json::Value>, StatusCode> {
    let token = extract_bearer_token(&headers).ok_or(StatusCode::UNAUTHORIZED)?;
    let claims = verify_jwt(&token)?;
    let athlete_id: i32 = claims.sub.parse().map_err(|_| StatusCode::UNAUTHORIZED)?;
    let conn = state.conn.lock().await;
    let now = Utc::now().to_rfc3339();
    let metrics = payload.get("metrics").and_then(|v| v.as_array()).cloned().unwrap_or_default();
    let mut synced = 0i64;
    for m in metrics {
        let metric_type = m.get("metric_type").and_then(|v| v.as_str()).unwrap_or("health_connect_sync");
        let value = m.get("value").and_then(|v| v.as_f64()).unwrap_or(1.0);
        let unit = m.get("unit").and_then(|v| v.as_str());
        let note = m.get("source").and_then(|v| v.as_str()).or(Some("health_connect")).unwrap_or("health_connect");
        let recorded_at = m.get("recorded_at").and_then(|v| v.as_str()).unwrap_or(&now);
        conn.execute(
            "INSERT INTO athlete_metric_log (athlete_id, tenant_id, metric_type, value, unit, note, source, recorded_at, created_at) VALUES (?1, ?1, ?2, ?3, ?4, ?5, 'health_connect', ?6, ?7)",
            params![athlete_id, metric_type, value, unit, note, recorded_at, now],
        ).map_err(|_| StatusCode::INTERNAL_SERVER_ERROR)?;
        synced += 1;
    }
    conn.execute(
        "UPDATE health_connect_tokens SET last_sync_at = ?, updated_at = ? WHERE athlete_id = ?",
        params![now, now, athlete_id],
    ).ok();
    Ok(axum::Json(serde_json::json!({"synced": synced, "connected": true})))
}


// ---- HR 24h continuous heart-rate tracking ----

#[derive(serde::Deserialize)]
struct HrSample {
    heart_rate: i64,
}

#[derive(serde::Deserialize)]
struct HrSamplesBulk {
    samples: Vec<HrSample>,
    source: Option<String>,
}

#[derive(serde::Deserialize)]
struct HrSettings {
    enabled: Option<bool>,
    interval_seconds: Option<i32>,
    source: Option<String>,
    device_id: Option<String>,
    max_hr: Option<i32>,
    resting_hr: Option<i32>,
}

async fn hr_get_settings(
    state: AxumState<AppState>,
    headers: HeaderMap,
) -> Result<axum::Json<serde_json::Value>, StatusCode> {
    let token = extract_bearer_token(&headers).ok_or(StatusCode::UNAUTHORIZED)?;
    let claims = verify_jwt(&token)?;
    let athlete_id: i32 = claims.sub.parse().map_err(|_| StatusCode::UNAUTHORIZED)?;
    let conn = state.conn.lock().await;
    let row = conn
        .query_row(
            "SELECT enabled, interval_seconds, source, device_id, max_hr, resting_hr FROM hr_monitoring_settings WHERE athlete_id = ?",
            params![athlete_id],
            |r| {
                let device_id: Option<String> = r.get(3)?;
                let max_hr: Option<i32> = r.get(4)?;
                let resting_hr: Option<i32> = r.get(5)?;
                Ok((
                    r.get::<_, i32>(0)?,
                    r.get::<_, i32>(1)?,
                    r.get::<_, String>(2)?,
                    device_id,
                    max_hr,
                    resting_hr,
                ))
            },
        )
        .optional()
        .map_err(|_| StatusCode::INTERNAL_SERVER_ERROR)?;
    if let Some((enabled, interval, src, device_id, max_hr, resting_hr)) = row {
        Ok(axum::Json(serde_json::json!({
            "enabled": enabled == 1,
            "interval_seconds": interval,
            "source": src,
            "device_id": device_id,
            "max_hr": max_hr,
            "resting_hr": resting_hr,
        })))
    } else {
        Ok(axum::Json(serde_json::json!({
            "enabled": true,
            "interval_seconds": 30,
            "source": "ble",
            "device_id": None::<Option<String>>,
            "max_hr": None::<Option<i64>>,
            "resting_hr": None::<Option<i64>>,
        })))
    }
}

async fn hr_upsert_settings(
    state: AxumState<AppState>,
    headers: HeaderMap,
    AxumJson(payload): AxumJson<HrSettings>,
) -> Result<axum::Json<serde_json::Value>, StatusCode> {
    let token = extract_bearer_token(&headers).ok_or(StatusCode::UNAUTHORIZED)?;
    let claims = verify_jwt(&token)?;
    let athlete_id: i32 = claims.sub.parse().map_err(|_| StatusCode::UNAUTHORIZED)?;
    let conn = state.conn.lock().await;
    let now = Utc::now().to_rfc3339();
    conn.execute(
        "INSERT INTO hr_monitoring_settings (athlete_id, tenant_id, enabled, interval_seconds, source, device_id, max_hr, resting_hr, created_at, updated_at) VALUES (?1, ?1, COALESCE(?2, 1), COALESCE(?3, 30), COALESCE(?4, 'ble'), ?5, ?6, ?7, ?8, ?8) ON CONFLICT(athlete_id) DO UPDATE SET enabled=excluded.enabled, interval_seconds=excluded.interval_seconds, source=excluded.source, device_id=excluded.device_id, max_hr=excluded.max_hr, resting_hr=excluded.resting_hr, updated_at=excluded.updated_at",
        params![athlete_id, payload.enabled.map(|v| if v {1} else {0}), payload.interval_seconds, payload.source.as_deref(), payload.device_id.as_deref(), payload.max_hr, payload.resting_hr, now],
    ).map_err(|_| StatusCode::INTERNAL_SERVER_ERROR)?;
    Ok(axum::Json(serde_json::json!({
        "enabled": payload.enabled.unwrap_or(true),
        "interval_seconds": payload.interval_seconds.unwrap_or(30),
        "source": payload.source.unwrap_or("ble".to_string()),
        "device_id": payload.device_id,
        "max_hr": payload.max_hr,
        "resting_hr": payload.resting_hr,
    })))
}

async fn hr_log_samples(
    state: AxumState<AppState>,
    headers: HeaderMap,
    AxumJson(payload): AxumJson<HrSamplesBulk>,
) -> Result<axum::Json<serde_json::Value>, StatusCode> {
    let token = extract_bearer_token(&headers).ok_or(StatusCode::UNAUTHORIZED)?;
    let claims = verify_jwt(&token)?;
    let athlete_id: i32 = claims.sub.parse().map_err(|_| StatusCode::UNAUTHORIZED)?;
    let conn = state.conn.lock().await;
    let now = Utc::now().to_rfc3339();
    let src = payload.source.as_deref().unwrap_or("ble");
    let mut count = 0i64;
    for s in &payload.samples {
        if s.heart_rate < 0 || s.heart_rate > 300 {
            continue;
        }
        conn.execute(
            "INSERT INTO hr_24h_samples (athlete_id, tenant_id, heart_rate, source, device_id, recorded_at, created_at) VALUES (?1, ?1, ?2, ?3, NULL, ?4, ?5)",
            params![athlete_id, s.heart_rate, src, now.clone(), now],
        ).map_err(|_| StatusCode::INTERNAL_SERVER_ERROR)?;
        count += 1;
    }
    Ok(axum::Json(serde_json::json!({"saved": count})))
}

async fn hr_get_24h(
    state: AxumState<AppState>,
    headers: HeaderMap,
    axum::extract::Query(q): axum::extract::Query<std::collections::HashMap<String, String>>,
) -> Result<axum::Json<serde_json::Value>, StatusCode> {
    let token = extract_bearer_token(&headers).ok_or(StatusCode::UNAUTHORIZED)?;
    let claims = verify_jwt(&token)?;
    let athlete_id: i32 = claims.sub.parse().map_err(|_| StatusCode::UNAUTHORIZED)?;
    let hours: i64 = q.get("hours").and_then(|v| v.parse().ok()).unwrap_or(24);
    let conn = state.conn.lock().await;
    let since = (Utc::now() - chrono::Duration::hours(hours)).to_rfc3339();
    let mut stmt = conn
        .prepare("SELECT heart_rate, source, device_id, recorded_at FROM hr_24h_samples WHERE athlete_id = ?1 AND recorded_at >= ?2 ORDER BY recorded_at ASC")
        .map_err(|_| StatusCode::INTERNAL_SERVER_ERROR)?;
    let rows = stmt
        .query_map(params![athlete_id, since], |r| {
            let device_id: Option<String> = r.get(2)?;
            Ok(serde_json::json!({
                "heart_rate": r.get::<_, i64>(0)?,
                "source": r.get::<_, String>(1)?,
                "device_id": device_id,
                "recorded_at": r.get::<_, String>(3)?,
            }))
        })
        .map_err(|_| StatusCode::INTERNAL_SERVER_ERROR)?;
    let samples: Vec<_> = rows.filter_map(|r| r.ok()).collect();
    Ok(axum::Json(serde_json::json!({"samples": samples})))
}

async fn hr_get_summary(
    state: AxumState<AppState>,
    headers: HeaderMap,
    axum::extract::Query(q): axum::extract::Query<std::collections::HashMap<String, String>>,
) -> Result<axum::Json<Option<serde_json::Value>>, StatusCode> {
    let token = extract_bearer_token(&headers).ok_or(StatusCode::UNAUTHORIZED)?;
    let claims = verify_jwt(&token)?;
    let athlete_id: i32 = claims.sub.parse().map_err(|_| StatusCode::UNAUTHORIZED)?;
    let days: i64 = q.get("days").and_then(|v| v.parse().ok()).unwrap_or(30);
    let conn = state.conn.lock().await;
    let since = (Utc::now() - chrono::Duration::days(days)).format("%Y-%m-%d").to_string();
    let row = conn
        .query_row(
            "SELECT date(recorded_at) as day, MIN(heart_rate), ROUND(AVG(heart_rate), 1), MAX(heart_rate), COUNT(*) FROM hr_24h_samples WHERE athlete_id = ?1 AND date(recorded_at) >= ?2 GROUP BY date(recorded_at) ORDER BY day ASC",
            params![athlete_id, since],
            |r| {
                let resting: Option<i64> = r.get(1)?;
                let avg: Option<f64> = r.get(2)?;
                let max: Option<i64> = r.get(3)?;
                let count: i64 = r.get(4)?;
                Ok(serde_json::json!({
                    "day": r.get::<_, String>(0)?,
                    "resting_hr": resting,
                    "avg_hr": avg,
                    "max_hr": max,
                    "min_hr": resting,
                    "sample_count": count,
                }))
            },
        )
        .optional()
        .map_err(|_| StatusCode::INTERNAL_SERVER_ERROR)?;
    Ok(axum::Json(row))
}

async fn hr_get_summary_history(
    state: AxumState<AppState>,
    headers: HeaderMap,
    axum::extract::Query(q): axum::extract::Query<std::collections::HashMap<String, String>>,
) -> Result<axum::Json<serde_json::Value>, StatusCode> {
    let token = extract_bearer_token(&headers).ok_or(StatusCode::UNAUTHORIZED)?;
    let claims = verify_jwt(&token)?;
    let athlete_id: i32 = claims.sub.parse().map_err(|_| StatusCode::UNAUTHORIZED)?;
    let days: i64 = q.get("days").and_then(|v| v.parse().ok()).unwrap_or(30);
    let conn = state.conn.lock().await;
    let since = (Utc::now() - chrono::Duration::days(days)).format("%Y-%m-%d").to_string();
    let mut stmt = conn
        .prepare("SELECT date(recorded_at) as day, MIN(heart_rate), ROUND(AVG(heart_rate), 1), MAX(heart_rate), COUNT(*) FROM hr_24h_samples WHERE athlete_id = ?1 AND date(recorded_at) >= ?2 GROUP BY date(recorded_at) ORDER BY day ASC")
        .map_err(|_| StatusCode::INTERNAL_SERVER_ERROR)?;
    let rows = stmt
        .query_map(params![athlete_id, since], |r| {
            let resting: Option<i64> = r.get(1)?;
            let avg: Option<f64> = r.get(2)?;
            let max: Option<i64> = r.get(3)?;
            let count: i64 = r.get(4)?;
            Ok(serde_json::json!({
                "day": r.get::<_, String>(0)?,
                "resting_hr": resting,
                "avg_hr": avg,
                "max_hr": max,
                "min_hr": resting,
                "sample_count": count,
            }))
        })
        .map_err(|_| StatusCode::INTERNAL_SERVER_ERROR)?;
    let history: Vec<_> = rows.filter_map(|r| r.ok()).collect();
    Ok(axum::Json(serde_json::json!({"history": history})))
}

async fn hr_delete_samples(
    state: AxumState<AppState>,
    headers: HeaderMap,
    axum::extract::Query(q): axum::extract::Query<std::collections::HashMap<String, String>>,
) -> Result<axum::Json<serde_json::Value>, StatusCode> {
    let token = extract_bearer_token(&headers).ok_or(StatusCode::UNAUTHORIZED)?;
    let claims = verify_jwt(&token)?;
    let athlete_id: i32 = claims.sub.parse().map_err(|_| StatusCode::UNAUTHORIZED)?;
    let conn = state.conn.lock().await;
    let older_than = q.get("older_than");
    let deleted = match older_than {
        Some(ts) => conn
            .execute("DELETE FROM hr_24h_samples WHERE athlete_id = ?1 AND recorded_at < ?2", params![athlete_id, ts])
            .map_err(|_| StatusCode::INTERNAL_SERVER_ERROR)?,
        None => conn
            .execute("DELETE FROM hr_24h_samples WHERE athlete_id = ?1", params![athlete_id])
            .map_err(|_| StatusCode::INTERNAL_SERVER_ERROR)?,
    };
    Ok(axum::Json(serde_json::json!({"deleted": deleted})))
}

// ---- Avvio server Axum ----

async fn start_axum_server(state: AppState, port: u16) -> Result<(), Box<dyn std::error::Error>> {
    let cors = CorsLayer::new()
        .allow_origin(tower_http::cors::Any)
        .allow_methods([
            Method::GET,
            Method::POST,
            Method::PUT,
            Method::DELETE,
            Method::OPTIONS,
        ])
        .allow_headers([axum::http::header::CONTENT_TYPE, axum::http::header::AUTHORIZATION]);

    let app = Router::new()
        .route("/health", get(health_handler))
        .route("/api/v1/auth/me", get(auth_me))
        .route("/api/v1/auth/google", get(google_auth_handler))
        .route("/api/v1/auth/login", post(auth_login))
        .route("/api/v1/auth/register", post(auth_register))
        .route("/api/v1/auth/logout", post(auth_logout))
        .route("/api/v1/import/strava/auth", get(import_not_supported).post(import_not_supported))
        .route("/api/v1/import/strava/callback", get(import_not_supported).post(import_not_supported))
        .route("/api/v1/import/strava/sync", post(import_not_supported))
        .route("/api/v1/import/strava/disconnect", delete(import_not_supported))
        .route("/api/v1/import/wahoo/auth", get(import_not_supported).post(import_not_supported))
        .route("/api/v1/import/wahoo/callback", get(import_not_supported).post(import_not_supported))
        .route("/api/v1/import/wahoo/sync", post(import_not_supported))
        .route("/api/v1/import/wahoo/disconnect", delete(import_not_supported))
        .route("/api/v1/import/garmin/auth", get(import_not_supported).post(import_not_supported))
        .route("/api/v1/import/garmin/callback", get(import_not_supported).post(import_not_supported))
        .route("/api/v1/import/garmin/sync", post(import_not_supported))
        .route("/api/v1/import/garmin/disconnect", delete(import_not_supported))
        .route("/api/v1/rides", get(list_rides).post(create_ride))
        .route("/api/v1/rides/{id}", get(get_ride))
        .route("/api/v1/sync/status", get(sync_status_handler))
        .route("/api/v1/sync/settings", post(sync_settings_handler))
        .route("/api/v1/sync/export", get(sync_export_handler))
        .route("/api/v1/sync/import", post(sync_import_handler))
        .route("/api/v1/ble/devices", get(ble_list_devices).post(ble_register_device))
        .route("/api/v1/ble/devices/{id}", put(ble_update_device).delete(ble_delete_device))
        .route("/api/v1/ble/devices/{id}/sync", post(ble_sync_device))
        .route("/api/v1/health-connect/status", get(health_connect_status))
        .route("/api/v1/health-connect/connect", post(health_connect_connect))
        .route("/api/v1/health-connect/disconnect", post(health_connect_disconnect))
        .route("/api/v1/health-connect/sync", post(health_connect_sync))
        .route("/api/v1/import/providers", get(list_import_providers))
        .route("/api/v1/hr/settings", get(hr_get_settings).put(hr_upsert_settings))
        .route("/api/v1/hr/samples", post(hr_log_samples).delete(hr_delete_samples))
        .route("/api/v1/hr/24h", get(hr_get_24h))
        .route("/api/v1/hr/summary", get(hr_get_summary))
        .route("/api/v1/hr/summary/history", get(hr_get_summary_history))
        .layer(cors)
        .with_state(state);

    let addr: SocketAddr = if port == 8001 {
        // Bind su tutte le interfacce (IPv4 + IPv6) così la WebView Tauri
        // raggiunge il backend sia via 127.0.0.1 che via ::1/localhost.
        "0.0.0.0:8001".parse().unwrap()
    } else {
        SocketAddr::from(([127, 0, 0, 1], port))
    };
    let listener = tokio::net::TcpListener::bind(addr)
        .await
        .map_err(|e| format!("Failed to bind to {}: {}", addr, e))?;

    eprintln!("[Axum] backend listening su http://127.0.0.1:{}", port);
    axum::serve(listener, app).await.map_err(|e| e.into())
}

// ---- Risoluzione percorso DB multipiattaforma ----

fn resolve_db_path<R: tauri::Runtime>(app: &impl tauri::Manager<R>) -> PathBuf {
    let base = app
        .path()
        .app_data_dir()
        .unwrap_or_else(|_| {
            dirs::data_dir()
                .unwrap_or_else(|| PathBuf::from("."))
                .join("bikemaster")
        });
    base.join("bikemaster.db")
}

// ---- JNI bridge per Android Health Connect ----

#[cfg(target_os = "android")]
mod health_connect_jni {
    use jni::JavaVM;
    use jni::objects::{JString, JValue};
    use jni::signature::JavaType;
    use jni::sys;
    use std::sync::Once;

    static mut JAVA_VM: Option<JavaVM> = None;
    static INIT: Once = Once::new();

    #[no_mangle]
    pub unsafe extern "system" fn JNI_OnLoad(vm: JavaVM, _reserved: *mut std::ffi::c_void) -> i32 {
        INIT.call_once(|| {
            JAVA_VM = Some(vm);
        });
        jni::sys::JNI_VERSION_1_6
    }

    pub fn get_java_vm() -> Option<&'static JavaVM> {
        unsafe { JAVA_VM.as_ref() }
    }

    pub fn read_metrics() -> serde_json::Value {
        let vm = match get_java_vm() {
            Some(vm) => vm,
            None => return serde_json::json!({"error": "JavaVM not initialized"}),
        };

        let mut env = match vm.attach_current_thread() {
            Ok(env) => env,
            Err(e) => return serde_json::json!({"error": format!("Failed to attach thread: {}", e)}),
        };

        let class = match env.find_class("com/bikemaster/health/HealthConnectHelper") {
            Ok(cls) => cls,
            Err(e) => return serde_json::json!({"error": format!("Class not found: {}", e)}),
        };

        let method_id = match env.get_static_method_id(class, "readMetrics", "()Ljava/util/Map;") {
            Ok(mid) => mid,
            Err(e) => return serde_json::json!({"error": format!("Method not found: {}", e)}),
        };

        let result = match env.call_static_method_unchecked(class, method_id, JavaType::Object("java/util/Map".to_string()), &[]) {
            Ok(val) => val,
            Err(e) => return serde_json::json!({"error": format!("Call failed: {}", e)}),
        };

        let map = match result {
            JValue::Object(obj) => obj,
            _ => return serde_json::json!({"error": "Expected Object".to_string()}),
        };

        let entry_set = match env.call_method(map, "entrySet", "()Ljava/util/Set;", &[]) {
            Ok(val) => val,
            Err(e) => return serde_json::json!({"error": format!("entrySet failed: {}", e)}),
        };

        let set = match entry_set {
            JValue::Object(obj) => obj,
            _ => return serde_json::json!({"error": "Expected Object".to_string()}),
        };

        let iterator = match env.call_method(set, "iterator", "()Ljava/util/Iterator;", &[]) {
            Ok(val) => val,
            Err(e) => return serde_json::json!({"error": format!("iterator failed: {}", e)}),
        };

        let iter_obj = match iterator {
            JValue::Object(obj) => obj,
            _ => return serde_json::json!({"error": "Expected Object".to_string()}),
        };

        let mut metrics = serde_json::Map::new();

        loop {
            let has_next = match env.call_method(iter_obj, "hasNext", "()Z", &[]) {
                Ok(val) => val.z().unwrap_or(false),
                Err(_) => break,
            };

            if !has_next {
                break;
            }

            let entry = match env.call_method(iter_obj, "next", "()Ljava/lang/Object;", &[]) {
                Ok(val) => val,
                Err(_) => break,
            };

            let entry_obj = match entry {
                JValue::Object(obj) => obj,
                _ => break,
            };

            let key = match env.call_method(entry_obj, "getKey", "()Ljava/lang/Object;", &[]) {
                Ok(val) => match val {
                    JValue::Object(obj) => {
                        let s = JString::from(obj);
                        match env.get_string(s) {
                            Ok(java_str) => java_str.to_str().unwrap_or("").to_string(),
                            Err(_) => continue,
                        }
                    }
                    _ => continue,
                },
                Err(_) => continue,
            };

            let value = match env.call_method(entry_obj, "getValue", "()Ljava/lang/Object;", &[]) {
                Ok(val) => val,
                Err(_) => continue,
            };

            let val_str = match value {
                JValue::Object(obj) => {
                    let s = JString::from(obj);
                    match env.get_string(s) {
                        Ok(java_str) => match java_str.to_str() {
                            Ok(str_val) => Some(serde_json::Value::String(str_val.to_string())),
                            Err(_) => None,
                        },
                        Err(_) => None,
                    }
                }
                JValue::Int(n) => Some(serde_json::Value::Number(n.into())),
                JValue::Long(n) => Some(serde_json::Value::Number(n.into())),
                JValue::Float(n) => serde_json::Number::from_f64(n as f64).map(serde_json::Value::Number),
                JValue::Double(n) => serde_json::Number::from_f64(n).map(serde_json::Value::Number),
                JValue::Bool(n) => Some(serde_json::Value::Bool(n == sys::JNI_TRUE)),
                _ => None,
            };

            if let Some(val) = val_str {
                metrics.insert(key, val);
            }
        }

        serde_json::Value::Object(metrics)
    }
}

#[cfg(not(target_os = "android"))]
mod health_connect_jni {
    pub fn read_metrics() -> serde_json::Value {
        serde_json::json!({})
    }
}

// ---- Entrypoint principale ----

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    tauri::Builder::default()
        .setup(|app| {
            let db_path = resolve_db_path(app);
            let conn = init_db(&db_path).expect("Impossibile inizializzare SQLite");

            let state = AppState {
                db_path: db_path.clone(),
                conn: Arc::new(Mutex::new(conn)),
            };

            let port: u16 = 8001;
            let server_state = state.clone();

            tauri::async_runtime::spawn(async move {
                if let Err(e) = start_axum_server(server_state, port).await {
                    eprintln!("[Axum] server error: {}", e);
                }
            });

            app.manage(state);
            app.manage(HrMonitorRegistry::default());

            Ok(())
        })
        .invoke_handler(tauri::generate_handler![get_app_info, get_db_path, reset_local_data, ble_scan, ble_pair, ble_read_measurement, ble_start_hr_monitoring, ble_stop_hr_monitoring, ble_get_device_info, health_connect_permissions, health_connect_read_metrics])
        .run(tauri::generate_context!())
        .expect("errore durante l'avvio dell'applicazione Tauri");
}
