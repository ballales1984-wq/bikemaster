// Entrypoint Tauri per la versione Desktop di BikeMaster.
//
// Include:
//   - Axum server embedded su localhost (porta 8001) come backend locale
//   - SQLite (rusqlite) come database primario su disco
//   - Tauri commands per comunicazione WebView <-> Rust
//   - Endpoint REST: /health, /api/v1/rides, /api/v1/auth/me

use axum::{
    extract::{Form, Query, State as AxumState},
    http::{HeaderMap, Method, StatusCode},
    routing::{get, post},
    Router,
};
use chrono::Utc;
use rusqlite::{params, Connection};
use std::net::SocketAddr;
use std::path::PathBuf;
use std::sync::Arc;
use tauri::State as TauriState;
use tauri::Manager;
use tokio::sync::Mutex;
use tower_http::cors::CorsLayer;
use uuid::Uuid;

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

// ---- Axum HTTP Handlers ----

const FAKE_JWT_TOKEN: &str =
    "eyJhbGciOiJub25lIn0.eyJzdWIiOiIxIiwiZW1haWwiOiJsb2NhbEBiaWtlbWFzdGVyLmxvY2FsIiwidGVuYW50X2lkIjoxLCJleHAiOjk5OTk5OTk5OTl9.";

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

async fn auth_me(headers: HeaderMap) -> Result<axum::Json<serde_json::Value>, StatusCode> {
    let token = extract_bearer_token(&headers).ok_or(StatusCode::UNAUTHORIZED)?;
    if token == FAKE_JWT_TOKEN {
        return Ok(axum::Json(serde_json::json!({
            "id": 1,
            "username": "local@bikemaster.local",
            "email": "local@bikemaster.local",
            "is_admin": false,
            "tenant_id": 1,
            "profile_complete": true,
        })));
    }
    Err(StatusCode::UNAUTHORIZED)
}

#[derive(serde::Deserialize)]
struct GoogleAuthQuery {
    redirect_uri: Option<String>,
}

async fn google_auth_handler(
    _query: Query<GoogleAuthQuery>,
) -> axum::Json<serde_json::Value> {
    axum::Json(serde_json::json!({
        "access_token": FAKE_JWT_TOKEN,
        "refresh_token": FAKE_JWT_TOKEN,
        "token_type": "bearer",
        "username": "local@bikemaster.local",
        "email": "local@bikemaster.local",
        "id": 1,
        "is_admin": false,
    }))
}

#[derive(serde::Deserialize)]
struct LoginFormData {
    username: String,
    password: String,
}

async fn auth_login(
    Form(form): Form<LoginFormData>,
) -> axum::Json<serde_json::Value> {
    if form.username.is_empty() || form.password.is_empty() {
        return axum::Json(serde_json::json!({"detail": "Username and password required"}));
    }
    axum::Json(serde_json::json!({
        "access_token": FAKE_JWT_TOKEN,
        "refresh_token": FAKE_JWT_TOKEN,
        "token_type": "bearer",
        "username": form.username,
        "id": 1,
        "is_admin": false,
    }))
}

async fn auth_register(
    Form(form): Form<LoginFormData>,
) -> axum::Json<serde_json::Value> {
    if form.username.is_empty() || form.password.is_empty() {
        return axum::Json(serde_json::json!({"detail": "Username and password required"}));
    }
    if form.password.len() < 6 {
        return axum::Json(serde_json::json!({"detail": "Password must be at least 6 characters"}));
    }
    axum::Json(serde_json::json!({
        "message": "User registered successfully",
        "username": form.username,
    }))
}

async fn auth_logout(_headers: HeaderMap) -> Result<StatusCode, StatusCode> {
    Ok(StatusCode::OK)
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
         );",
    )?;
    Ok(conn)
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
        .route("/api/v1/rides", get(list_rides).post(create_ride))
        .route("/api/v1/rides/{id}", get(get_ride))
        .layer(cors)
        .with_state(state);

    let addr = SocketAddr::from(([127, 0, 0, 1], port));
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

            Ok(())
        })
        .invoke_handler(tauri::generate_handler![get_app_info, get_db_path, reset_local_data])
        .run(tauri::generate_context!())
        .expect("errore durante l'avvio dell'applicazione Tauri");
}
