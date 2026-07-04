"""Frontend dashboard generator."""

from __future__ import annotations

DASHBOARD_HTML = """<!DOCTYPE html>
<html lang="en">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>BikeMaster - Dashboard</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: #1a1a2e; color: #eee; min-height: 100vh; }
        .container { max-width: 1200px; margin: 0 auto; padding: 20px; }
        header { text-align: center; padding: 40px 0; border-bottom: 1px solid #333; }
        h1 { color: #4ecca3; font-size: 2.5rem; margin-bottom: 10px; }
        .stats { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 20px; margin: 40px 0; }
        .stat-card { background: #16213e; padding: 25px; border-radius: 10px; text-align: center; }
        .stat-value { font-size: 2rem; color: #4ecca3; font-weight: bold; }
        .stat-label { color: #888; margin-top: 5px; }
        .rides-list { margin-top: 30px; }
        .ride-item { background: #16213e; padding: 15px; margin: 10px 0; border-radius: 8px; display: flex; justify-content: space-between; align-items: center; }
        .ride-date { font-weight: bold; color: #fff; }
        .ride-stats { color: #aaa; font-size: 0.9rem; }
        .btn { background: #4ecca3; color: #1a1a2e; border: none; padding: 8px 16px; border-radius: 5px; cursor: pointer; }
        .btn:hover { background: #3dbba0; }
        .refresh { text-align: center; margin: 20px 0; }
        .weather-section { margin-top: 30px; }
        .weather-controls { display: flex; gap: 10px; margin-bottom: 15px; }
        .weather-controls input { padding: 8px; border-radius: 5px; border: none; }
        .weather-card { background: #16213e; padding: 15px; border-radius: 8px; }
        .weather-item { margin: 5px 0; }
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>🚴 BikeMaster</h1>
            <p>Cycling Performance Dashboard</p>
        </header>
        <div class="refresh"><button class="btn" onclick="loadRides()">Refresh Data</button></div>
        <div class="weather-section" id="weather-section">
            <h3 style="color:#4ecca3;margin-bottom:10px;">🌤️ Meteo</h3>
            <div class="weather-controls">
                <input id="weather-lat" type="number" step="0.0001" placeholder="Lat" value="45.4642" />
                <input id="weather-lon" type="number" step="0.0001" placeholder="Lon" value="9.1900" />
                <input id="weather-date" type="date" />
                <button class="btn" onclick="fetchWeather()">Ottieni Meteo</button>
            </div>
            <div id="weather-result" class="weather-card" style="display:none;">
                <div class="weather-item" id="weather-temp"></div>
                <div class="weather-item" id="weather-humidity"></div>
                <div class="weather-item" id="weather-description"></div>
                <div class="weather-item" id="weather-advice" style="font-weight:bold;margin-top:10px;"></div>
            </div>
        </div>
        <div class="stats" id="stats">
            <div class="stat-card"><div class="stat-value" id="total-rides">0</div><div class="stat-label">Total Rides</div></div>
            <div class="stat-card"><div class="stat-value" id="total-distance">0</div><div class="stat-label">Total Km</div></div>
            <div class="stat-card"><div class="stat-value" id="total-calories">0</div><div class="stat-label">Total Calories</div></div>
            <div class="stat-card"><div class="stat-value" id="avg-speed">0</div><div class="stat-label">Average Speed</div></div>
        </div>
        <div class="rides-list" id="rides-list"></div>
    </div>
    <script>
        async function loadRides() {
            const resp = await fetch('/api/v1/rides');
            const data = await resp.json();
            document.getElementById('total-rides').textContent = data.total;
            const rides = data.rides || [];
            const totalKm = rides.reduce((s, r) => s + (r.distance_km || 0), 0);
            const totalCal = rides.reduce((s, r) => s + (r.calories || 0), 0);
            const avgSp = rides.length ? rides.reduce((s, r) => s + (r.avg_speed_kmh || 0), 0) / rides.length : 0;
            document.getElementById('total-distance').textContent = totalKm.toFixed(1);
            document.getElementById('total-calories').textContent = totalCal.toFixed(0);
            document.getElementById('avg-speed').textContent = avgSp.toFixed(1);
            const list = document.getElementById('rides-list');
            list.innerHTML = rides.map(r => `
                <div class="ride-item">
                    <div><div class="ride-date">${r.date}</div><div class="ride-stats">${r.distance_km}km • ${r.duration_minutes}min • ${r.avg_speed_kmh} km/h</div></div>
                    <button class="btn" onclick="deleteRide(${r.id})">Delete</button>
                </div>`).join('');
        }
        async function deleteRide(id) {
            await fetch(`/api/v1/rides/${id}`, { method: 'DELETE' });
            loadRides();
        }
        async function fetchWeather() {
            const lat = document.getElementById('weather-lat').value;
            const lon = document.getElementById('weather-lon').value;
            const date = document.getElementById('weather-date').value;
            const resultDiv = document.getElementById('weather-result');
            try {
                const params = new URLSearchParams({ lat, lon });
                if (date) params.append('date', date);
                const resp = await fetch('/api/v1/weather?' + params);
                const data = await resp.json();
                document.getElementById('weather-temp').textContent = '🌡️ Temperatura: ' + data.temperature + '°C';
                document.getElementById('weather-humidity').textContent = '💧 Umidità: ' + data.humidity + '%';
                document.getElementById('weather-description').textContent = '📝 ' + data.description;
                document.getElementById('weather-advice').textContent = data.advice;
                resultDiv.style.display = 'block';
            } catch (e) {
                resultDiv.style.display = 'block';
                document.getElementById('weather-advice').textContent = 'Errore: ' + e.message;
            }
        }
        loadRides();
    </script>
</body>
</html>"""


def generate_dashboard_html(output_path: str = "dashboard.html") -> str:
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(DASHBOARD_HTML)
    return output_path


if __name__ == "__main__":
    generate_dashboard_html()
    print("Dashboard generated: dashboard.html")
