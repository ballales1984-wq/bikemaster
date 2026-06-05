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

    document.addEventListener('DOMContentLoaded', init);

    function init() {
        setupForm();
        setupResetButton();
        loadRides();
    }

    function setupForm() {
        const form = document.getElementById('ride-form');
        if (!form) return;
        form.addEventListener('submit', onFormSubmit);
        form.addEventListener('input', clearFieldError);
    }

    function clearFieldError(e) {
        const id = e.target.id;
        const errorEl = document.getElementById('error-' + id.replace('ride-', ''));
        if (errorEl) {
            errorEl.textContent = '';
            e.target.classList.remove('invalid');
        }
    }

    function setupResetButton() {
        const btn = document.getElementById('reset-demo-btn');
        if (!btn) return;
        btn.addEventListener('click', onResetDemo);
    }

    async function loadRides() {
        const listEl = document.getElementById('rides-list');
        const loadingEl = document.getElementById('rides-loading');
        if (loadingEl) loadingEl.style.display = 'block';

        try {
            const data = await apiGet('/api/v1/rides');
            currentRides = data.rides || [];

            updateStats(currentRides);
            renderRides(currentRides);
            updateDurationChart(currentRides);
        } catch (err) {
            console.error('loadRides error:', err);
            showToast('Errore nel caricamento delle ride', 'error');
            if (listEl) {
                listEl.innerHTML = '<p class="empty-text">Impossibile caricare le ride. Riprova pi&ugrave; tardi.</p>';
            }
        } finally {
            if (loadingEl) loadingEl.style.display = 'none';
        }
    }

    function updateStats(rides) {
        const totalKm = rides.reduce((s, r) => s + (parseFloat(r.distance_km) || 0), 0);
        const totalCal = rides.reduce((s, r) => s + (parseFloat(r.calories) || 0), 0);
        const avgSp = rides.length
            ? rides.reduce((s, r) => s + (parseFloat(r.avg_speed_kmh) || 0), 0) / rides.length
            : 0;
        const totalDur = rides.reduce((s, r) => s + (parseFloat(r.duration_minutes) || 0), 0);

        setText('total-rides', rides.length);
        setText('total-distance', formatNumber(totalKm, 1));
        setText('total-calories', formatNumber(totalCal, 0));
        setText('avg-speed', formatNumber(avgSp, 1));
        setText('total-hours', formatNumber(totalDur / 60, 1));
    }

    function setText(id, value) {
        const el = document.getElementById(id);
        if (el) el.textContent = value;
    }

    function renderRides(rides) {
        const listEl = document.getElementById('rides-list');
        if (!listEl) return;

        if (rides.length === 0) {
            listEl.innerHTML = '<p class="empty-text">Nessuna ride. Aggiungine una sopra!</p>';
            return;
        }

        listEl.innerHTML = rides.map(r => {
            const fatigue = r.heart_rate_avg
                ? ((parseFloat(r.duration_minutes) || 0) / 60 * 1.5).toFixed(1)
                : '0';
            const hasGps = r.gps_points && r.gps_points.length > 0;
            const gpsIcon = hasGps ? ' 📡' : '';
            const safeDate = escapeHtml(r.date);
            const safeDist = escapeHtml(r.distance_km);
            const safeDur = escapeHtml(r.duration_minutes);
            const safeSpeed = escapeHtml(r.avg_speed_kmh);

            return '<div class="ride-item" role="listitem" tabindex="0" data-ride-id="' + r.id + '" aria-label="Ride del ' + safeDate + ', ' + safeDist + ' km">' +
                '<div class="ride-date">' + safeDate + gpsIcon + '</div>' +
                '<div class="ride-details">' + safeDist + ' km &bull; ' + safeDur + ' min &bull; ' + safeSpeed + ' km/h &bull; Fatigue: ' + fatigue + '/10</div>' +
            '</div>';
        }).join('');

        listEl.querySelectorAll('.ride-item').forEach(item => {
            item.addEventListener('click', () => onRideClick(item));
            item.addEventListener('keydown', (e) => {
                if (e.key === 'Enter' || e.key === ' ') {
                    e.preventDefault();
                    onRideClick(item);
                }
            });
        });
    }

    async function onRideClick(item) {
        const rideId = item.getAttribute('data-ride-id');
        try {
            const ride = await apiGet('/api/v1/rides/' + rideId);
            showMap(ride);
        } catch (err) {
            console.error('Failed to load ride details:', err);
            showToast('Impossibile caricare i dettagli della ride', 'error');
        }
    }

    async function onFormSubmit(e) {
        e.preventDefault();

        const form = e.target;
        const errors = validateForm(form);

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
            const msg = err.message || 'Errore durante l\'aggiunta della ride';
            showToast(msg, 'error');
        } finally {
            setButtonLoading('add-ride-btn', false);
        }
    }

    function validateForm(form) {
        const errors = {};
        const date = form.elements['date'];
        const dist = form.elements['distance_km'];
        const dur = form.elements['duration_minutes'];
        const speed = form.elements['avg_speed_kmh'];
        const hr = form.elements['heart_rate_avg'];
        const elev = form.elements['elevation_gain_m'];

        if (!date || !date.value.trim()) {
            errors['date'] = 'La data &egrave; obbligatoria';
        } else if (!/^\d{4}-\d{2}-\d{2}$/.test(date.value)) {
            errors['date'] = 'Formato data non valido (YYYY-MM-DD)';
        }

        if (!dist || dist.value === '' || isNaN(parseFloat(dist.value))) {
            errors['distance_km'] = 'Inserisci una distanza valida';
        } else if (parseFloat(dist.value) < 0) {
            errors['distance_km'] = 'La distanza non pu&ograve; essere negativa';
        }

        if (!dur || dur.value === '' || isNaN(parseFloat(dur.value))) {
            errors['duration_minutes'] = 'Inserisci una durata valida';
        } else if (parseFloat(dur.value) <= 0) {
            errors['duration_minutes'] = 'La durata deve essere maggiore di 0';
        }

        if (speed && speed.value !== '' && (isNaN(parseFloat(speed.value)) || parseFloat(speed.value) < 0)) {
            errors['avg_speed_kmh'] = 'Velocit&agrave; non valida';
        }

        if (hr && hr.value !== '' && (isNaN(parseFloat(hr.value)) || parseFloat(hr.value) < 30 || parseFloat(hr.value) > 220)) {
            errors['heart_rate_avg'] = 'HR deve essere tra 30 e 220 bpm';
        }

        if (elev && elev.value !== '' && (isNaN(parseFloat(elev.value)) || parseFloat(elev.value) < 0)) {
            errors['elevation_gain_m'] = 'Altitudine non valida';
        }

        return errors;
    }

    async function onResetDemo() {
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
    }

    function showMap(ride) {
        const mapDiv = document.getElementById('map');
        if (!mapDiv) return;

        mapDiv.classList.toggle('visible');

        if (!map) {
            map = L.map('map').setView([45.5, 9.2], 13);
            mapTileLayer = L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
                attribution: '&copy; OpenStreetMap contributors',
                maxZoom: 19
            }).addTo(map);
        }

        if (mapDiv.classList.contains('visible')) {
            setTimeout(() => map.invalidateSize(), 100);
        }

        if (!ride.gps_points || ride.gps_points.length === 0) {
            map.eachLayer(layer => {
                if (layer instanceof L.Marker || layer instanceof L.Polyline || layer instanceof L.CircleMarker) {
                    map.removeLayer(layer);
                }
            });
            L.popup()
                .setLatLng(map.getCenter())
                .setContent('<strong>Nessun dato GPS</strong><br>Aggiungi punti GPS a questa ride per visualizzare il percorso.')
                .openOn(map);
            return;
        }

        map.eachLayer(layer => {
            if (layer instanceof L.Marker || layer instanceof L.Polyline || layer instanceof L.CircleMarker) {
                map.removeLayer(layer);
            }
        });

        const latLngs = ride.gps_points.map(p => [p.lat, p.lon]);

        const polyline = L.polyline(latLngs, {
            color: '#4ecca3',
            weight: 4,
            opacity: 0.8
        }).addTo(map);

        latLngs.forEach((ll, i) => {
            const point = ride.gps_points[i];
            const speed = point.speed != null ? point.speed.toFixed(1) + ' km/h' : '';
            const alt = point.altitude != null ? point.altitude.toFixed(0) + ' m' : '';
            const popupContent = '<strong>Punto ' + (i + 1) + '</strong>' +
                (speed ? '<br>Velocit&agrave;: ' + escapeHtml(speed) : '') +
                (alt ? '<br>Altitudine: ' + escapeHtml(alt) : '');

            L.circleMarker(ll, {
                radius: 4,
                fillColor: '#4ecca3',
                color: '#1a1a2e',
                weight: 1,
                opacity: 1,
                fillOpacity: 0.8
            }).bindPopup(popupContent).addTo(map);
        });

        const bounds = polyline.getBounds();
        map.fitBounds(bounds, { padding: [30, 30] });
    }

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
                data: {
                    labels,
                    datasets: [{
                        label: 'Durata (min)',
                        data,
                        backgroundColor: '#4ecca3',
                        borderRadius: 6
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    scales: {
                        y: {
                            beginAtZero: true,
                            ticks: { color: '#888' },
                            grid: { color: '#2a2a4a' }
                        },
                        x: {
                            ticks: { color: '#888' },
                            grid: { display: false }
                        }
                    },
                    plugins: {
                        legend: {
                            labels: { color: '#aaa' }
                        }
                    },
                    animation: { duration: 400 }
                }
            });
        }
    }

    function setButtonLoading(btnId, loading) {
        const btn = document.getElementById(btnId);
        if (!btn) return;
        if (loading) {
            btn.classList.add('loading');
            btn.disabled = true;
        } else {
            btn.classList.remove('loading');
            btn.disabled = false;
        }
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
        if (icons[type]) {
            toast.insertAdjacentHTML('afterbegin', '<strong>' + icons[type] + '</strong> ');
        }

        setTimeout(() => {
            toast.classList.add('removing');
            toast.addEventListener('animationend', () => {
                if (toast.parentNode) toast.parentNode.removeChild(toast);
            });
        }, 4000);
    }

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
        try {
            return JSON.parse(text);
        } catch {
            return {};
        }
    }
})();
