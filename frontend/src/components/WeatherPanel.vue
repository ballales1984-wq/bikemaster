<template>
  <div class="panel">
    <h2>🌤️ Weather</h2>

    <div class="form-grid">
      <div class="form-group">
        <label for="weather-lat">Latitude</label>
        <input
          id="weather-lat"
          v-model.number="lat"
          type="number"
          step="0.0001"
          placeholder="Ex: 45.4642"
        >
      </div>
      <div class="form-group">
        <label for="weather-lon">Longitude</label>
        <input
          id="weather-lon"
          v-model.number="lon"
          type="number"
          step="0.0001"
          placeholder="Ex: 9.1900"
        >
      </div>
      <div class="form-group">
        <label for="weather-date">Date (optional)</label>
        <input
id="weather-date" type="date" v-model="date" />
      </div>
      <div class="form-group">
        <button
          class="btn btn-primary"
          :disabled="loading"
          @click="fetchWeather"
        >
          {{ loading ? "🔄 Loading..." : "🌡️ Get Weather" }}
        </button>
      </div>
    </div>

    <div v-if="loading"
class="loading-text">
      <span class="spinner" /> Loading weather...
    </div>

    <div v-else-if="weatherError"
class="error-box">
      {{ weatherError }}
    </div>

    <div v-else-if="!weather"
class="empty-state">
      <div class="empty-icon">🌤️</div>
      <div class="empty-title">Weather Information</div>
      <div class="empty-desc">
        Enter coordinates and click "Get Weather" for current conditions and
        cycling-specific advice
      </div>
    </div>

    <div v-else
class="weather-card">
      <div class="weather-header">
        <h3>{{ weather.location?.city || "Location" }}</h3>
        <span
class="weather-score" :class="'score-' + weather.score"
        >Score: {{ weather.score }}/10</span>
      </div>
      <div class="weather-info">
        <div class="weather-item">
          <span class="weather-icon">🌡️</span>
          <span class="weather-value">{{ weather.temperature }}°C</span>
        </div>
        <div class="weather-item">
          <span class="weather-icon">🔥</span>
          <span class="weather-value">{{ weather.feels_like }}°C (feels like)</span>
        </div>
        <div class="weather-item">
          <span class="weather-icon">💧</span>
          <span class="weather-value">{{ weather.humidity }}%</span>
        </div>
        <div class="weather-item">
          <span class="weather-icon">💨</span>
          <span class="weather-value">{{ weather.wind_speed }} m/s</span>
        </div>
        <div class="weather-item">
          <span class="weather-icon">📊</span>
          <span class="weather-value">{{ weather.pressure }} hPa</span>
        </div>
      </div>
      <div class="weather-advice">
        <p>{{ weather.advice }}</p>
      </div>
    </div>

    <div class="panel"
style="margin-top: 20px">
      <h3>📅 7-Day Forecast</h3>
      <div v-if="forecastLoading"
class="loading-text">
        Loading forecasts...
      </div>
      <div v-else
class="forecast-grid">
        <div v-for="f in forecast"
:key="f.date" class="forecast-card">
          <div class="forecast-date">
            {{ f.date }}
          </div>
          <div class="forecast-temp">{{ f.temperature }}°C</div>
          <div class="forecast-humidity">💧 {{ f.humidity }}%</div>
          <div class="forecast-advice">
            {{ f.advice }}
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, watch } from "vue";
import { apiGet } from "../utils/api";

const lat = ref(45.4642);
const lon = ref(9.19);
const date = ref("");
const loading = ref(false);
const weather = ref(null);
const weatherError = ref("");
const forecast = ref([]);
const forecastLoading = ref(false);

async function fetchWeather() {
  loading.value = true;
  weatherError.value = "";
  weather.value = null;

  try {
    const params = { lat: lat.value, lon: lon.value };
    if (date.value) params.date = date.value;
    weather.value = await apiGet("/api/v1/weather", params);
  } catch (e) {
    weatherError.value = e.message || "Error loading weather";
  } finally {
    loading.value = false;
  }
}

async function fetchForecast() {
  forecastLoading.value = true;
  try {
    const data = await apiGet("/api/v1/weather/forecast", {
      lat: lat.value,
      lon: lon.value,
      days: 7,
    });
    forecast.value = data.forecasts || [];
  } catch (e) {
    forecast.value = [];
  } finally {
    forecastLoading.value = false;
  }
}

watch(date, (newDate) => {
  if (newDate && lat.value && lon.value) {
    fetchWeather();
  }
});
</script>

<style scoped>
.weather-card {
  background: #16213e;
  padding: 20px;
  border-radius: 10px;
  margin-top: 15px;
}

.weather-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 15px;
}

.weather-header h3 {
  color: #4ecca3;
  margin: 0;
}

.weather-info {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(120px, 1fr));
  gap: 15px;
}

.weather-item {
  display: flex;
  align-items: center;
  gap: 8px;
}

.weather-icon {
  font-size: 1.2rem;
}

.weather-score {
  padding: 4px 12px;
  border-radius: 15px;
  font-weight: bold;
}

.score-8,
.score-9,
.score-10 {
  background: #dcfce7;
  color: #166534;
}
.score-5,
.score-6,
.score-7 {
  background: #fef3c7;
  color: #92400e;
}
.score-0,
.score-1,
.score-2,
.score-3,
.score-4 {
  background: #fee2e2;
  color: #991b1b;
}

.forecast-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(140px, 1fr));
  gap: 10px;
  margin-top: 15px;
}

.forecast-card {
  background: #0f172a;
  padding: 12px;
  border-radius: 8px;
  text-align: center;
}

.forecast-date {
  font-weight: bold;
  color: #4ecca3;
  margin-bottom: 8px;
}

.forecast-temp {
  font-size: 1.3rem;
  margin: 5px 0;
}

.forecast-humidity,
.forecast-score {
  font-size: 0.85rem;
  margin: 3px 0;
}

.forecast-advice {
  font-size: 0.75rem;
  color: #888;
  margin-top: 5px;
}

.error-box {
  background: #fee2e2;
  color: #991b1b;
  padding: 12px;
  border-radius: 8px;
  margin-top: 10px;
}
</style>
