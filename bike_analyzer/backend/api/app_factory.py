"""FastAPI application factory."""
from __future__ import annotations
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, Response
from .routes import router

DASHBOARD_HTML = """<!DOCTYPE html>
<html lang="it">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>BikeMaster - Dashboard</title>
    <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />
    <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: #1a1a2e; color: #eee; min-height: 100vh; padding: 20px; }
        .container { max-width: 1200px; margin: 0 auto; }
        header { text-align: center; padding: 40px 0; border-bottom: 1px solid #333; }
        h1 { color: #4ecca3; font-size: 2.5rem; margin-bottom: 10px; }
        .stats { display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: 15px; margin: 30px 0; }
        .stat-card { background: #16213e; padding: 20px; border-radius: 10px; text-align: center; }
        .stat-value { font-size: 1.8rem; color: #4ecca3; font-weight: bold; }
        .stat-label { color: #888; margin-top: 5px; font-size: 0.9rem; }
        .panel { background: #16213e; padding: 20px; border-radius: 10px; margin: 20px 0; }
        .panel h2 { color: #4ecca3; margin-bottom: 15px; font-size: 1.3rem; }
        .form-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(120px, 1fr)); gap: 10px; }
        .form-grid input { background: #0f0f23; border: 1px solid #333; color: #fff; padding: 10px; border-radius: 5px; }
        .rides-list { margin-top: 20px; max-height: 400px; overflow-y: auto; }
        .ride-item { background: #0f0f23; padding: 12px; margin: 8px 0; border-radius: 8px; cursor: pointer; }
        .ride-item:hover { background: #1a1a3e; }
        .ride-date { font-weight: bold; color: #fff; }
        .ride-details { color: #aaa; font-size: 0.85rem; margin-top: 5px; }
        .map-container { height: 300px; margin-top: 15px; border-radius: 8px; display: none; }
        .btn { background: #4ecca3; color: #1a1a2e; border: none; padding: 8px 16px; border-radius: 5px; cursor: pointer; margin: 5px; }
        .btn:hover { background: #3dbba0; }
        .flex { display: flex; gap: 10px; align-items: center; flex-wrap: wrap; }
    </style>
</head>
<body>
    <div class="container">
        <header><h1>🚴 BikeMaster</h1><p>Cycling Performance Intelligence</p></header>
        
        <div class="stats" id="stats"></div>
        
        <div class="panel">
            <h2>➕ Aggiungi Nuova Ride</h2>
            <div class="form-grid">
                <input type="date" id="ride-date" placeholder="Data">
                <input type="number" id="ride-distance" placeholder="Distanza (km)" step="0.1">
                <input type="number" id="ride-duration" placeholder="Durata (min)" step="1">
                <input type="number" id="ride-speed" placeholder="Velocità (km/h)" step="0.1">
                <input type="number" id="ride-calories" placeholder="Calorie" step="1">
                <input type="number" id="ride-hr" placeholder="HR medio" step="1">
                <input type="number" id="ride-elevation" placeholder="Altitudine (m)" step="1">
            </div>
            <div class="flex"><button class="btn" onclick="addRide()">Aggiungi</button></div>
        </div>

        <div class="panel">
            <h2>📋 Le tue Ride</h2>
            <div class="rides-list" id="rides-list"></div>
        </div>
        
        <div id="map" class="map-container"></div>
    </div>
    
    <script>
        let map = null;
        async function loadRides() {
            const resp = await fetch('/api/v1/rides');
            const data = await resp.json();
            const rides = data.rides || [];
            
            // Stats
            const totalKm = rides.reduce((s, r) => s + (r.distance_km || 0), 0);
            const totalCal = rides.reduce((s, r) => s + (r.calories || 0), 0);
            const avgSp = rides.length ? rides.reduce((s, r) => s + (r.avg_speed_kmh || 0), 0) / rides.length : 0;
            const totalDur = rides.reduce((s, r) => s + (r.duration_minutes || 0), 0);
            
            document.getElementById('stats').innerHTML = [
                {v: rides.length, l: 'Rides'},
                {v: totalKm.toFixed(1), l: 'Km Totali'},
                {v: totalCal.toFixed(0), l: 'Calorie'},
                {v: avgSp.toFixed(1), l: 'Vel Media'},
                {v: (totalDur/60).toFixed(1), l: 'Ore Totali'}
            ].map(s => `<div class="stat-card"><div class="stat-value">${s.v}</div><div class="stat-label">${s.l}</div></div>`).join('');
            
            // Rides list
            document.getElementById('rides-list').innerHTML = rides.map(r => {
                const fatigue = r.heart_rate_avg ? ((r.duration_minutes || 0) / 60 * 1.5).toFixed(1) : '0';
                const pause = r.gps_points ? '📡' : '';
                return `<div class="ride-item" onclick="showMap(${r.id})">
                    <div class="ride-date">${r.date} ${pause}</div>
                    <div class="ride-details">${r.distance_km}km • ${r.duration_minutes}min • ${r.avg_speed_kmh} km/h • Fatigue: ${fatigue}/10</div>
                </div>`;
            }).join('') || '<p>Nessuna ride. Aggiungi una sopra!</p>';
        }
        
        async function addRide() {
            const ride = {
                date: document.getElementById('ride-date').value || new Date().toISOString().split('T')[0],
                distance_km: parseFloat(document.getElementById('ride-distance').value) || 0,
                duration_minutes: parseFloat(document.getElementById('ride-duration').value) || 0,
                avg_speed_kmh: parseFloat(document.getElementById('ride-speed').value) || 0,
                calories: parseFloat(document.getElementById('ride-calories').value) || 0,
                heart_rate_avg: parseFloat(document.getElementById('ride-hr').value) || null,
                elevation_gain_m: parseFloat(document.getElementById('ride-elevation').value) || null
            };
            await fetch('/api/v1/rides', { method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify(ride) });
            loadRides();
        }
        
        async function showMap(id) {
            const mapDiv = document.getElementById('map');
            if (!map) { map = L.map('map').setView([45.5, 9.2], 13); L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png').addTo(map); }
            mapDiv.style.display = mapDiv.style.display === 'none' ? 'block' : 'none';
        }
        
        loadRides();
    </script>
</body>
</html>"""

def create_app() -> FastAPI:
    app = FastAPI(title="BikeMaster API", description="GPS-based cycling intelligence", version="0.1.0")
    app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])
    app.include_router(router, prefix="/api/v1")
    
    @app.get("/", response_class=HTMLResponse)
    async def dashboard():
        return DASHBOARD_HTML
    
    @app.get("/dashboard", response_class=HTMLResponse)
    async def dashboard_alt():
        return DASHBOARD_HTML
    
    @app.get("/favicon.ico")
    async def favicon():
        return Response(content='<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100"><circle cx="50" cy="50" r="40" fill="#4ecca3"/><text x="50" y="55" font-size="40" text-anchor="middle">🚴</text></svg>', 
                       media_type="image/svg+xml")
    
    return app