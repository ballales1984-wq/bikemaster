(function () {
    'use strict';

    const API_BASE = '';

    function escapeHtml(str) {
        if (str == null) return '';
        const s = String(str);
        const div = document.createElement('div');
        div.appendChild(document.createTextNode(s));
        return div.innerHTML;
    }

    function formatNumber(num, decimals) {
        if (num == null || isNaN(num)) return '0';
        return Number(num).toFixed(decimals ?? 1);
    }

    let map = null;
    let mapTileLayer = null;
    let durationChart = null;
    let currentRides = [];
    let activeRideId = null;

    document.addEventListener('DOMContentLoaded', init);

    function init() {
        setupTabs();
        setupRideForm();
        setupResetDemo();
        setupExportButtons();
        setupImportUpload();
        setupAthleteForm();
        setupAthleteActions();
        setupCoachActions();
        setupKnowledgeActions();
        setupAdminActions();
        setupBenchmark();
        setupDetailActions();
        loadRides();
    }

    /* ==================== TABS ==================== */

    function setupTabs() {
        const tabs = document.querySelectorAll('.tab');
        const panels = document.querySelectorAll('.tab-panel');
        tabs.forEach(tab => {
            tab.addEventListener('click', () => {
                const target = tab.getAttribute('data-tab');
                tabs.forEach(t => { t.classList.remove('active'); t.setAttribute('aria-selected', 'false'); });
                panels.forEach(p => p.classList.remove('active'));
                tab.classList.add('active');
                tab.setAttribute('aria-selected', 'true');
                const panel = document.getElementById(target);
                if (panel) panel.classList.add('active');
            });
        });
    }

    /* ==================== API HELPERS ==================== */

    async function apiGet(path) {
        const resp = await fetch(API_BASE + path);
        if (!resp.ok) {
            const text = await resp.text().catch(() => '');
            throw new Error('HTTP ' + resp.status + (text ? ': ' + text : ''));
        }
        return resp.json();
    }

    async function apiPost(path, body) {
        const resp = await fetch(API_BASE + path, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(body)
        });
        const text = await resp.text().catch(() => '');
        if (!resp.ok) {
            throw new Error(text || 'HTTP ' + resp.status);
        }
        try { return JSON.parse(text); } catch { return {}; }
    }

    async function apiPut(path, body) {
        const resp = await fetch(API_BASE + path, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(body)
        });
        const text = await resp.text().catch(() => '');
        if (!resp.ok) throw new Error(text || 'HTTP ' + resp.status);
        try { return JSON.parse(text); } catch { return {}; }
    }

    async function apiDelete(path) {
        const resp = await fetch(API_BASE + path, { method: 'DELETE' });
        if (!resp.ok) {
            const text = await resp.text().catch(() => '');
            throw new Error(text || 'HTTP ' + resp.status);
        }
        return {};
    }

    async function apiPostFile(path, formData) {
        const resp = await fetch(API_BASE + path, {
            method: 'POST',
            body: formData
        });
        const text = await resp.text().catch(() => '');
        if (!resp.ok) throw new Error(text || 'HTTP ' + resp.status);
        try { return JSON.parse(text); } catch { return {}; }
    }

    /* ==================== TOAST & UI ==================== */

    function setText(id, value) {
        const el = document.getElementById(id);
        if (el) el.textContent = value;
    }

    function setButtonLoading(btnId, loading) {
        const btn = document.getElementById(btnId);
        if (!btn) return;
        if (loading) { btn.classList.add('loading'); btn.disabled = true; }
        else { btn.classList.remove('loading'); btn.disabled = false; }
    }

    function showToast(message, type) {
        type = type || 'info';
        const container = document.getElementById('toast-container');
        if (!container) return;
        const toast = document.createElement('div');
        toast.className = 'toast ' + type;
        toast.textContent = message;
        container.appendChild(toast);
        const icons = { success: '✓', error: '✕', warning: '⚠', info: 'ℹ' };
        if (icons[type]) toast.insertAdjacentHTML('afterbegin', '<strong>' + icons[type] + '</strong> ');
        setTimeout(() => {
            toast.classList.add('removing');
            toast.addEventListener('animationend', () => { if (toast.parentNode) toast.parentNode.removeChild(toast); });
        }, 4000);
    }

    /* ==================== RIDES ==================== */

    async function loadRides() {
        const listEl = document.getElementById('rides-list');
        const loadingEl = document.getElementById('rides-loading');
        if (loadingEl) loadingEl.style.display = 'block';
        try {
            const data = await apiGet('/api/v1/rides?page=1&page_size=50&sort=date');
            currentRides = data.rides || [];
            updateStats(currentRides);
            renderRides(currentRides);
            updateDurationChart(currentRides);
        } catch (err) {
            console.error('loadRides error:', err);
            showToast('Errore nel caricamento delle ride', 'error');
            if (listEl) listEl.innerHTML = '<p class="empty-text">Impossibile caricare le ride. Riprova più tardi.</p>';
        } finally {
            if (loadingEl) loadingEl.style.display = 'none';
        }
    }

    function updateStats(rides) {
        const totalKm = rides.reduce((s, r) => s + (parseFloat(r.distance_km) || 0), 0);
        const totalCal = rides.reduce((s, r) => s + (parseFloat(r.calories) || 0), 0);
        const avgSp = rides.length ? rides.reduce((s, r) => s + (parseFloat(r.avg_speed_kmh) || 0), 0) / rides.length : 0;
        const totalDur = rides.reduce((s, r) => s + (parseFloat(r.duration_minutes) || 0), 0);
        setText('total-rides', rides.length);
        setText('total-distance', formatNumber(totalKm, 1));
        setText('total-calories', formatNumber(totalCal, 0));
        setText('avg-speed', formatNumber(avgSp, 1));
        setText('total-hours', formatNumber(totalDur / 60, 1));
    }

    function renderRides(rides) {
        const listEl = document.getElementById('rides-list');
        if (!listEl) return;
        if (rides.length === 0) {
            listEl.innerHTML = '<p class="empty-text">Nessuna ride. Aggiungine una sopra!</p>';
            return;
        }
        listEl.innerHTML = rides.map(r => {
            const fatigue = r.heart_rate_avg ? ((parseFloat(r.duration_minutes) || 0) / 60 * 1.5).toFixed(1) : '0';
            const hasGps = r.gps_points && r.gps_points.length > 0;
            const gpsIcon = hasGps ? ' 📡' : '';
            return '<div class="ride-item" role="listitem" tabindex="0" data-ride-id="' + r.id + '" aria-label="Ride del ' + escapeHtml(r.date) + ', ' + escapeHtml(r.distance_km) + ' km">' +
                '<div><div class="ride-date">' + escapeHtml(r.date) + gpsIcon + '</div>' +
                '<div class="ride-details">' + escapeHtml(r.distance_km) + ' km &bull; ' + escapeHtml(r.duration_minutes) + ' min &bull; ' + escapeHtml(r.avg_speed_kmh) + ' km/h &bull; Fatigue: ' + fatigue + '/10</div></div>' +
                '<button class="btn btn-sm btn-secondary" data-action="detail" data-ride-id="' + r.id + '">Dettagli</button>' +
                '<button class="btn btn-sm btn-secondary" data-action="delete" data-ride-id="' + r.id + '">Elimina</button>' +
            '</div>';
        }).join('');

        listEl.querySelectorAll('[data-action="detail"]').forEach(btn => {
            btn.addEventListener('click', (e) => { e.stopPropagation(); onRideDetail(parseInt(btn.getAttribute('data-ride-id'), 10)); });
        });
        listEl.querySelectorAll('[data-action="delete"]').forEach(btn => {
            btn.addEventListener('click', (e) => { e.stopPropagation(); deleteRide(parseInt(btn.getAttribute('data-ride-id'), 10)); });
        });
    }

    async function deleteRide(id) {
        if (!confirm('Eliminare la ride #' + id + '?')) return;
        try {
            await apiDelete('/api/v1/rides/' + id);
            showToast('Ride eliminata', 'success');
            await loadRides();
        } catch (err) {
            console.error('deleteRide error:', err);
            showToast('Impossibile eliminare la ride', 'error');
        }
    }

    function setupRideForm() {
        const form = document.getElementById('ride-form');
        if (!form) return;
        form.addEventListener('submit', onFormSubmit);
        form.addEventListener('input', clearFieldError);
    }

    function clearFieldError(e) {
        const id = e.target.id;
        const errorEl = document.getElementById('error-' + id.replace('ride-', ''));
        if (errorEl) { errorEl.textContent = ''; e.target.classList.remove('invalid'); }
    }

    async function onFormSubmit(e) {
        e.preventDefault();
        const form = e.target;
        const errors = validateRideForm(form);
        if (Object.keys(errors).length > 0) {
            Object.entries(errors).forEach(([name, msg]) => {
                const input = form.querySelector('[name="' + name + '"]');
                const errorEl = document.getElementById('error-' + name.replace('_', '-'));
                if (input) input.classList.add('invalid');
                if (errorEl) errorEl.textContent = msg;
            });
            const firstInvalid = form.querySelector('.invalid');
            if (firstInvalid) firstInvalid.focus();
            showToast('Compila correttamente i campi obbligatori', 'warning');
            return;
        }
        setButtonLoading('add-ride-btn', true);
        try {
            const ride = {
                date: form.elements['date'].value,
                distance_km: parseFloat(form.elements['distance_km'].value),
                duration_minutes: parseFloat(form.elements['duration_minutes'].value),
                avg_speed_kmh: parseFloat(form.elements['avg_speed_kmh'].value) || undefined,
                calories: parseFloat(form.elements['calories'].value) || undefined,
                heart_rate_avg: parseFloat(form.elements['heart_rate_avg'].value) || null,
                elevation_gain_m: parseFloat(form.elements['elevation_gain_m'].value) || null
            };
            await apiPost('/api/v1/rides', ride);
            form.reset();
            const today = new Date().toISOString().split('T')[0];
            if (form.elements['date']) form.elements['date'].value = today;
            showToast('Ride aggiunta con successo!', 'success');
            await loadRides();
        } catch (err) {
            console.error('addRide error:', err);
            showToast(err.message || "Errore durante l'aggiunta della ride", 'error');
        } finally {
            setButtonLoading('add-ride-btn', false);
        }
    }

    function validateRideForm(form) {
        const errors = {};
        const date = form.elements['date'];
        const dist = form.elements['distance_km'];
        const dur = form.elements['duration_minutes'];
        const speed = form.elements['avg_speed_kmh'];
        const hr = form.elements['heart_rate_avg'];
        const elev = form.elements['elevation_gain_m'];

        if (!date || !date.value.trim()) errors['date'] = 'La data è obbligatoria';
        else if (!/^\d{4}-\d{2}-\d{2}$/.test(date.value)) errors['date'] = 'Formato data non valido (YYYY-MM-DD)';

        if (!dist || dist.value === '' || isNaN(parseFloat(dist.value))) errors['distance_km'] = 'Inserisci una distanza valida';
        else if (parseFloat(dist.value) < 0) errors['distance_km'] = 'La distanza non può essere negativa';

        if (!dur || dur.value === '' || isNaN(parseFloat(dur.value))) errors['duration_minutes'] = 'Inserisci una durata valida';
        else if (parseFloat(dur.value) <= 0) errors['duration_minutes'] = 'La durata deve essere maggiore di 0';

        if (speed && speed.value !== '' && (isNaN(parseFloat(speed.value)) || parseFloat(speed.value) < 0)) errors['avg_speed_kmh'] = 'Velocità non valida';

        if (hr && hr.value !== '' && (isNaN(parseFloat(hr.value)) || parseFloat(hr.value) < 30 || parseFloat(hr.value) > 220)) errors['heart_rate_avg'] = 'HR deve essere tra 30 e 220 bpm';

        if (elev && elev.value !== '' && (isNaN(parseFloat(elev.value)) || parseFloat(elev.value) < 0)) errors['elevation_gain_m'] = 'Altitudine non valida';

        return errors;
    }

    /* ==================== RIDE DETAIL & CHARTS ==================== */

    async function onRideDetail(rideId) {
        activeRideId = rideId;
        const detailPanel = document.getElementById('ride-detail-panel');
        const detailContent = document.getElementById('detail-content');
        const detailMap = document.getElementById('detail-map');

        try {
            const ride = await apiGet('/api/v1/rides/' + rideId);
            const fatigue = ride.fatigue_score != null ? ride.fatigue_score.toFixed(1) : '0';
            const ck = ride.calories_per_km != null ? ride.calories_per_km.toFixed(0) : '0';
            detailContent.innerHTML =
                '<div class="detail-meta">' +
                    '<div><strong>Data:</strong> ' + escapeHtml(ride.date) + '</div>' +
                    '<div><strong>Distanza:</strong> ' + escapeHtml(ride.distance_km) + ' km</div>' +
                    '<div><strong>Durata:</strong> ' + escapeHtml(ride.duration_minutes) + ' min</div>' +
                    '<div><strong>Vel Media:</strong> ' + escapeHtml(ride.avg_speed_kmh) + ' km/h</div>' +
                    '<div><strong>Calorie:</strong> ' + escapeHtml(ride.calories) + '</div>' +
                    '<div><strong>HR Media:</strong> ' + (ride.heart_rate_avg || '-') + ' bpm</div>' +
                    '<div><strong>Altitudine:</strong> ' + (ride.elevation_gain_m || 0) + ' m</div>' +
                    '<div><strong>Fatigue:</strong> ' + fatigue + '/10</div>' +
                    '<div><strong>Cal/km:</strong> ' + ck + '</div>' +
                '</div>';

            detailPanel.classList.remove('hidden');
            detailPanel.scrollIntoView({ behavior: 'smooth', block: 'start' });

            document.querySelectorAll('.chart-toolbar .btn-sm').forEach(b => b.setAttribute('data-ride', rideId));

            if (ride.gps_points && ride.gps_points.length > 0) {
                await renderRideCharts(ride);
                showRideMap(ride);
            } else {
                showToast('Nessun dato GPS per questa ride', 'info');
            }
        } catch (err) {
            console.error('Detail error:', err);
            showToast('Impossibile caricare i dettagli della ride', 'error');
        }
    }

function setupDetailActions() {
         const closeBtn = document.getElementById('close-detail-btn');
         if (closeBtn) {
             closeBtn.addEventListener('click', () => {
                 const panel = document.getElementById('ride-detail-panel');
                 if (panel) panel.classList.add('hidden');
                 activeRideId = null;
             });
         }
         document.querySelectorAll('.chart-toolbar .btn-sm').forEach(btn => {
             btn.addEventListener('click', async () => {
                 const rideId = parseInt(btn.getAttribute('data-ride'), 10);
                 const chartType = btn.getAttribute('data-chart');
                 if (!rideId) return;
                 try {
                     if (chartType === 'google-map') {
                         const mapData = await apiGet('/api/v1/rides/' + rideId + '/map/google');
                         if (mapData && mapData.map_url) {
                             const iframe = document.getElementById('folium-map-frame');
                             if (iframe) {
                                 iframe.src = mapData.map_url;
                                 document.getElementById('map-frame-container').style.display = 'block';
                             }
                         }
                         return;
                     }
                     const ride = await apiGet('/api/v1/rides/' + rideId);
                     await renderRideCharts(ride);
                 } catch (err) {
                     showToast('Errore nel caricamento del grafico/mappa', 'error');
                 }
             });
         });
     }

    async function renderRideCharts(ride) {
        const points = ride.gps_points || [];
        const labels = points.map((_, i) => 'P' + (i + 1));

        function mkChart(canvasId, label, data, color) {
            const canvas = document.getElementById(canvasId);
            if (!canvas) return;
            const ctx = canvas.getContext('2d');
            if (canvas._chart) canvas._chart.destroy();
            canvas._chart = new Chart(ctx, {
                type: 'bar',
                data: { labels, datasets: [{ label, data, backgroundColor: color, borderRadius: 4 }] },
                options: {
                    responsive: true, maintainAspectRatio: false,
                    scales: {
                        y: { beginAtZero: true, ticks: { color: '#888' }, grid: { color: '#2a2a4a' } },
                        x: { ticks: { color: '#888', maxRotation: 0, autoSkip: true, maxTicksLimit: 20 }, grid: { display: false } }
                    },
                    plugins: { legend: { labels: { color: '#aaa' } } },
                    animation: { duration: 400 }
                }
            });
        }

        mkChart('rideSpeedChart', 'Velocità (km/h)', points.map(p => p.speed != null ? p.speed : 0), '#FF6B00');
        mkChart('rideElevationChart', 'Altitudine (m)', points.map(p => p.altitude != null ? p.altitude : 0), '#4ecca3');
        mkChart('rideDistanceChart', 'Distanza Cumulata (km)', points.map((p, i) => {
            if (i === 0) return 0;
            const prev = points[i - 1];
            const R = 6371000;
            const toRad = d => d * Math.PI / 180;
            const dLat = toRad(p.lat - prev.lat);
            const dLon = toRad(p.lon - prev.lon);
            const aVal = Math.sin(dLat / 2) ** 2 + Math.cos(toRad(prev.lat)) * Math.cos(toRad(p.lat)) * Math.sin(dLon / 2) ** 2;
            return R * 2 * Math.atan2(Math.sqrt(aVal), Math.sqrt(1 - aVal)) / 1000;
        }).reduce((acc, v, i) => { acc.push((acc[i - 1] || 0) + v); return acc; }, []), '#0066CC');
    }

    function showRideMap(ride) {
        const mapDiv = document.getElementById('detail-map');
        if (!mapDiv || !mapDiv._leaflet_map) {
            if (!map) {
                map = L.map('detail-map').setView([45.5, 9.2], 13);
                mapTileLayer = L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
                    attribution: '&copy; OpenStreetMap contributors', maxZoom: 19
                }).addTo(map);
            }
        }

        if (!mapDiv._leaflet_map) {
            mapDiv.classList.add('visible');
            setTimeout(() => { if (map) map.invalidateSize(); }, 100);
            mapDiv._leaflet_map = true;
        }

        const latLngs = ride.gps_points.map(p => [p.lat, p.lon]);
        map.eachLayer(layer => {
            if (layer instanceof L.Marker || layer instanceof L.Polyline || layer instanceof L.CircleMarker) map.removeLayer(layer);
        });

        const polyline = L.polyline(latLngs, { color: '#4ecca3', weight: 4, opacity: 0.8 }).addTo(map);
        latLngs.forEach((ll, i) => {
            const point = ride.gps_points[i];
            const speed = point.speed != null ? point.speed.toFixed(1) + ' km/h' : '';
            const alt = point.altitude != null ? point.altitude.toFixed(0) + ' m' : '';
            const popupContent = '<strong>Punto ' + (i + 1) + '</strong>' + (speed ? '<br>Velocità: ' + escapeHtml(speed) : '') + (alt ? '<br>Altitudine: ' + escapeHtml(alt) : '');
            L.circleMarker(ll, { radius: 4, fillColor: '#4ecca3', color: '#1a1a2e', weight: 1, opacity: 1, fillOpacity: 0.8 }).bindPopup(popupContent).addTo(map);
        });

        const bounds = polyline.getBounds();
        map.fitBounds(bounds, { padding: [30, 30] });
    }

    /* ==================== DURATION CHART ==================== */

    function updateDurationChart(rides) {
        const canvas = document.getElementById('durationChart');
        if (!canvas || !canvas.getContext) return;
        const labels = rides.map(r => r.date).slice(-10);
        const data = rides.map(r => parseFloat(r.duration_minutes) || 0).slice(-10);

        if (durationChart) {
            const sameLabels = JSON.stringify(durationChart.data.labels) === JSON.stringify(labels);
            const sameData = JSON.stringify(durationChart.data.datasets[0].data) === JSON.stringify(data);
            if (sameLabels && sameData) return;
            durationChart.data.labels = labels;
            durationChart.data.datasets[0].data = data;
            durationChart.update('none');
        } else {
            const ctx = canvas.getContext('2d');
            durationChart = new Chart(ctx, {
                type: 'bar',
                data: { labels, datasets: [{ label: 'Durata (min)', data, backgroundColor: '#4ecca3', borderRadius: 6 }] },
                options: {
                    responsive: true, maintainAspectRatio: false,
                    scales: {
                        y: { beginAtZero: true, ticks: { color: '#888' }, grid: { color: '#2a2a4a' } },
                        x: { ticks: { color: '#888' }, grid: { display: false } }
                    },
                    plugins: { legend: { labels: { color: '#aaa' } } },
                    animation: { duration: 400 }
                }
            });
        }
    }

    /* ==================== RESET DEMO ==================== */

    function setupResetDemo() {
        const btn = document.getElementById('reset-demo-btn');
        if (!btn) return;
        btn.addEventListener('click', async () => {
            try {
                setButtonLoading('reset-demo-btn', true);
                await apiPost('/api/v1/admin/reset-demo');
                showToast('Dati demo resettati', 'info');
                await loadRides();
            } catch (err) {
                console.error('resetDemo error:', err);
                showToast('Errore nel reset dei dati demo', 'error');
            } finally {
                setButtonLoading('reset-demo-btn', false);
            }
        });
    }

    /* ==================== EXPORT ==================== */

    function setupExportButtons() {
        const jsonBtn = document.getElementById('export-json-btn');
        const csvBtn = document.getElementById('export-csv-btn');

        if (jsonBtn) {
            jsonBtn.addEventListener('click', async () => {
                try {
                    const resp = await fetch(API_BASE + '/api/v1/rides/export/json');
                    if (!resp.ok) throw new Error('Export failed');
                    const blob = await resp.blob();
                    const url = URL.createObjectURL(blob);
                    const a = document.createElement('a');
                    a.href = url; a.download = 'rides.json';
                    document.body.appendChild(a); a.click(); document.body.removeChild(a);
                    URL.revokeObjectURL(url);
                    showToast('JSON esportato', 'success');
                } catch (err) {
                    showToast('Errore esportazione JSON', 'error');
                }
            });
        }

        if (csvBtn) {
            csvBtn.addEventListener('click', async () => {
                try {
                    const resp = await fetch(API_BASE + '/api/v1/rides/export/csv');
                    if (!resp.ok) throw new Error('Export failed');
                    const blob = await resp.blob();
                    const url = URL.createObjectURL(blob);
                    const a = document.createElement('a');
                    a.href = url; a.download = 'rides.csv';
                    document.body.appendChild(a); a.click(); document.body.removeChild(a);
                    URL.revokeObjectURL(url);
                    showToast('CSV esportato', 'success');
                } catch (err) {
                    showToast('Errore esportazione CSV', 'error');
                }
            });
        }
    }

    /* ==================== IMPORT ==================== */

    function setupImportUpload() {
        const uploadArea = document.getElementById('upload-area');
        const fileInput = document.getElementById('import-file');
        if (!uploadArea || !fileInput) return;

        uploadArea.addEventListener('dragover', (e) => { e.preventDefault(); uploadArea.classList.add('drag-over'); });
        uploadArea.addEventListener('dragleave', () => uploadArea.classList.remove('drag-over'));
        uploadArea.addEventListener('drop', (e) => {
            e.preventDefault();
            uploadArea.classList.remove('drag-over');
            if (e.dataTransfer.files.length) handleImportFiles(e.dataTransfer.files);
        });

        fileInput.addEventListener('change', () => {
            if (fileInput.files.length) handleImportFiles(fileInput.files);
            fileInput.value = '';
        });
    }

    async function handleImportFiles(files) {
        const progressEl = document.getElementById('import-progress');
        progressEl.classList.remove('hidden');
        progressEl.innerHTML = '<p class="loading-text">Importazione in corso...</p>';

        try {
            const formData = new FormData();
            Array.from(files).forEach(f => formData.append('files', f));
            const result = await apiPostFile('/api/v1/import/multiple', formData);
            const count = result.count || result.imported ? result.imported.length : 0;
            progressEl.innerHTML = '<p style="color:var(--success)">Importati ' + count + ' file con successo!</p>' +
                (result.imported || []).map(r => '<div class="result-item">' + escapeHtml(r.date) + ' — ' + escapeHtml(r.distance_km) + ' km</div>').join('');
            showToast(count + ' file importati!', 'success');
            await loadRides();
        } catch (err) {
            console.error('Import error:', err);
            progressEl.innerHTML = '<p style="color:var(--error)">Errore importazione: ' + escapeHtml(err.message) + '</p>';
            showToast('Errore durante l\'importazione', 'error');
        }
    }

    /* ==================== ATHLETE ==================== */

    function setupAthleteForm() {
        const saveBtn = document.getElementById('save-athlete-btn');
        if (saveBtn) {
            saveBtn.addEventListener('click', async () => {
                const nameInput = document.getElementById('athlete-name');
                if (!nameInput || !nameInput.value.trim()) {
                    showToast('Nome atleta obbligatorio', 'warning');
                    return;
                }
                const data = collectAthleteForm();
                try {
                    setButtonLoading('save-athlete-btn', true);
                    const result = await apiPost('/api/v1/athletes', data);
                    document.getElementById('athlete-result').innerHTML = '<strong>Atleta creato:</strong> ID ' + result.id;
                    document.getElementById('athlete-result').classList.remove('hidden');
                    showToast('Atleta salvato (ID: ' + result.id + ')', 'success');
                } catch (err) {
                    showToast('Errore salvataggio atleta', 'error');
                } finally {
                    setButtonLoading('save-athlete-btn', false);
                }
            });
        }

        const loadBtn = document.getElementById('load-athlete-btn');
        if (loadBtn) {
            loadBtn.addEventListener('click', async () => {
                try {
                    const rides = await apiGet('/api/v1/rides?page=1&page_size=1&sort=date');
                    const lastRide = (rides.rides || [])[0];
                    if (!lastRide || !lastRide.athlete_id) {
                        showToast('Nessun atleta trovato', 'info');
                        return;
                    }
                    const athlete = await apiGet('/api/v1/athletes/' + lastRide.athlete_id);
                    populateAthleteForm(athlete);
                    document.getElementById('athlete-result').innerHTML = '<strong>Caricato:</strong> ' + escapeHtml(athlete.name) + ' (ID: ' + athlete.id + ')';
                    document.getElementById('athlete-result').classList.remove('hidden');
                } catch (err) {
                    showToast('Errore caricamento atleta', 'error');
                }
            });
        }

        const scoresBtn = document.getElementById('athlete-scores-btn');
        if (scoresBtn) {
            scoresBtn.addEventListener('click', async () => {
                const athleteIdInput = document.getElementById('athlete-id-hidden');
                const nameInput = document.getElementById('athlete-name');
                if (!nameInput || !nameInput.value.trim()) {
                    showToast('Salva prima l\'atleta per vedere i punteggi', 'warning');
                    return;
                }
                try {
                    const rides = await apiGet('/api/v1/rides?page=1&page_size=100&sort=date');
                    const ridesList = rides.rides || [];
                    const withAthlete = ridesList.filter(r => r.athlete_id);
                    if (!withAthlete.length) { showToast('Nessuna ride con atleta', 'info'); return; }
                    const lastRide = withAthlete[withAthlete.length - 1];
                    const scores = await apiGet('/api/v1/scores/athlete/' + lastRide.athlete_id);
                    const resultEl = document.getElementById('athlete-result');
                    resultEl.textContent = JSON.stringify(scores, null, 2);
                    resultEl.classList.remove('hidden');
                } catch (err) {
                    showToast('Errore caricamento punteggi', 'error');
                }
            });
        }
    }

    function collectAthleteForm() {
        const get = (id) => { const el = document.getElementById(id); return el ? el.value : ''; };
        return {
            name: get('athlete-name'),
            age: parseInt(get('athlete-age'), 10) || 30,
            weight_kg: parseFloat(get('athlete-weight')) || 70,
            height_cm: parseFloat(get('athlete-height')) || null,
            fat_percentage: parseFloat(get('athlete-fat')) || null,
            years_active: parseInt(get('athlete-years'), 10) || 1,
            weekly_sessions: parseInt(get('athlete-weekly'), 10) || 3,
            monthly_hours: parseFloat(get('athlete-monthly')) || 0,
            annual_hours: parseFloat(get('athlete-annual')) || 0,
            experience_level: get('athlete-level') || 'Beginner'
        };
    }

    function populateAthleteForm(athlete) {
        const set = (id, val) => { const el = document.getElementById(id); if (el) el.value = val; };
        set('athlete-name', athlete.name || '');
        set('athlete-age', athlete.age || 30);
        set('athlete-weight', athlete.weight_kg || 70);
        set('athlete-height', athlete.height_cm || '');
        set('athlete-fat', athlete.fat_percentage || '');
        set('athlete-years', athlete.years_active || 1);
        set('athlete-weekly', athlete.weekly_sessions || 3);
        set('athlete-monthly', athlete.monthly_hours || 0);
        set('athlete-annual', athlete.annual_hours || 0);
        set('athlete-level', athlete.experience_level || 'Beginner');
    }

    function setupAthleteActions() {}

    /* ==================== AI COACH ==================== */

    function setupCoachActions() {
        const workoutBtn = document.getElementById('workout-btn');
        if (workoutBtn) {
            workoutBtn.addEventListener('click', async () => {
                const athleteId = parseInt(document.getElementById('coach-athlete-id').value, 10) || 0;
                try {
                    setButtonLoading('workout-btn', true);
                    const result = await apiGet('/api/v1/coach/workout?athlete_id=' + athleteId);
                    const el = document.getElementById('workout-result');
                    el.textContent = JSON.stringify(result, null, 2);
                    el.classList.remove('hidden');
                } catch (err) {
                    showToast('Errore workout recommendations', 'error');
                } finally {
                    setButtonLoading('workout-btn', false);
                }
            });
        }

        const recoveryBtn = document.getElementById('recovery-btn');
        if (recoveryBtn) {
            recoveryBtn.addEventListener('click', async () => {
                const fatigue = parseFloat(document.getElementById('recovery-fatigue').value) || 5;
                const rideId = parseInt(document.getElementById('recovery-ride-id').value, 10) || 0;
                try {
                    setButtonLoading('recovery-btn', true);
                    const result = await apiGet('/api/v1/coach/recovery?fatigue_score=' + fatigue + '&ride_id=' + rideId);
                    const el = document.getElementById('recovery-result');
                    el.textContent = JSON.stringify(result, null, 2);
                    el.classList.remove('hidden');
                } catch (err) {
                    showToast('Errore recovery recommendations', 'error');
                } finally {
                    setButtonLoading('recovery-btn', false);
                }
            });
        }

        const trendsBtn = document.getElementById('trends-btn');
        if (trendsBtn) {
            trendsBtn.addEventListener('click', async () => {
                try {
                    setButtonLoading('trends-btn', true);
                    const result = await apiGet('/api/v1/coach/trends');
                    const el = document.getElementById('trends-result');
                    el.textContent = JSON.stringify(result, null, 2);
                    el.classList.remove('hidden');
                } catch (err) {
                    showToast('Errore storico trend', 'error');
                } finally {
                    setButtonLoading('trends-btn', false);
                }
            });
        }
    }

    /* ==================== KNOWLEDGE ==================== */

    function setupKnowledgeActions() {
        const searchBtn = document.getElementById('kb-search-btn');
        if (searchBtn) {
            searchBtn.addEventListener('click', async () => {
                const query = document.getElementById('kb-query').value.trim();
                if (!query) { showToast('Inserisci una query', 'warning'); return; }
                try {
                    const result = await apiGet('/api/v1/knowledge/search?q=' + encodeURIComponent(query));
                    const el = document.getElementById('knowledge-result');
                    el.textContent = JSON.stringify(result, null, 2);
                    el.classList.remove('hidden');
                } catch (err) {
                    showToast('Errore ricerca knowledge', 'error');
                }
            });
        }

        const listBtn = document.getElementById('kb-list-btn');
        if (listBtn) {
            listBtn.addEventListener('click', async () => {
                try {
                    const result = await apiGet('/api/v1/knowledge');
                    const el = document.getElementById('knowledge-result');
                    el.textContent = JSON.stringify(result, null, 2);
                    el.classList.remove('hidden');
                } catch (err) {
                    showToast('Errore lista knowledge', 'error');
                }
            });
        }
    }

    /* ==================== ADMIN ==================== */

    function setupAdminActions() {
        const statsBtn = document.getElementById('admin-stats-btn');
        if (statsBtn) {
            statsBtn.addEventListener('click', async () => {
                try {
                    const result = await apiGet('/api/v1/admin/stats');
                    const el = document.getElementById('admin-result');
                    el.textContent = JSON.stringify(result, null, 2);
                    el.classList.remove('hidden');
                } catch (err) {
                    showToast('Errore statistiche', 'error');
                }
            });
        }

        const backupBtn = document.getElementById('admin-backup-btn');
        if (backupBtn) {
            backupBtn.addEventListener('click', async () => {
                try {
                    const resp = await fetch(API_BASE + '/api/v1/admin/backup');
                    if (!resp.ok) throw new Error('Backup failed');
                    const blob = await resp.blob();
                    const url = URL.createObjectURL(blob);
                    const a = document.createElement('a');
                    a.href = url; a.download = 'backup.db';
                    document.body.appendChild(a); a.click(); document.body.removeChild(a);
                    URL.revokeObjectURL(url);
                    showToast('Backup scaricato', 'success');
                } catch (err) {
                    showToast('Errore backup', 'error');
                }
            });
        }

        const indexesBtn = document.getElementById('admin-indexes-btn');
        if (indexesBtn) {
            indexesBtn.addEventListener('click', async () => {
                try {
                    const result = await apiPost('/api/v1/admin/indexes');
                    const el = document.getElementById('admin-result');
                    el.textContent = JSON.stringify(result, null, 2);
                    el.classList.remove('hidden');
                    showToast('Indici creati', 'success');
                } catch (err) {
                    showToast('Errore creazione indici', 'error');
                }
            });
        }
    }

    /* ==================== BENCHMARK ==================== */

    function setupBenchmark() {
        const btn = document.getElementById('benchmark-btn');
        if (btn) {
            btn.addEventListener('click', async () => {
                const distance = parseFloat(document.getElementById('benchmark-distance').value) || 0;
                const speed = parseFloat(document.getElementById('benchmark-speed').value) || 0;
                const durationHours = parseFloat(document.getElementById('benchmark-duration').value) || 0;
                try {
                    setButtonLoading('benchmark-btn', true);
                    const result = await apiPost('/api/v1/benchmark/compare', {
                        distance_km: distance,
                        avg_speed_kmh: speed,
                        duration_hours: durationHours
                    });
                    const el = document.getElementById('benchmark-result');
                    el.textContent = JSON.stringify(result, null, 2);
                    el.classList.remove('hidden');
                } catch (err) {
                    showToast('Errore benchmark', 'error');
                } finally {
                    setButtonLoading('benchmark-btn', false);
                }
            });
        }
    }

})();
