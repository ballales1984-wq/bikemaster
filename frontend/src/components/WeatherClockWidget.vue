<!-- WeatherClockWidget: orologio compatto + meteo per citta, con menu selezione e GPS.
     Layout: header compatto. Persistenza citta in localStorage. -->
<template>
  <div class="wcw">
    <div class="wcw-main" @click="toggleMenu">
      <span class="wcw-clock">{{ clockTime }}</span>
      <span v-if="weather" class="wcw-weather">
        <span class="wcw-icon">{{ computedWeatherIcon }}</span>
        <span class="wcw-temp">{{ Math.round(computedTemperature) }}°C</span>
      </span>
      <span v-else class="wcw-weather wcw-weather--empty">
        <span class="wcw-icon">🌡️</span>
      </span>
      <span class="wcw-chevron" :class="{ 'wcw-chevron--open': menuOpen }"
        >▾</span
      >
    </div>

    <div v-if="menuOpen" class="wcw-menu">
      <div class="wcw-city-row">
        <input
          v-model="cityInput"
          type="text"
          placeholder="Citta (es. Milano)"
          @keydown.enter="onCitySubmit"
        />
        <button class="wcw-btn wcw-btn--primary" @click="onCitySubmit">
          OK
        </button>
      </div>
      <button class="wcw-btn wcw-btn--gps" @click="onGps">📍 GPS</button>
      <div v-if="weatherError" class="wcw-error">
        {{ weatherError }}
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from "vue";
import { apiGet } from "../utils/api";

const STORAGE_KEY = "bikemaster_weather_city";
const DEFAULT_CITY = "Milano";

const cityInput = ref("");
const selectedCity = ref<string>("");
const menuOpen = ref(false);
const weather = ref<Record<string, unknown> | null>(null);
const weatherError = ref("");
const loading = ref(false);
const clockTime = ref("");

let clockTimer: number | undefined;

function loadCity() {
  try {
    const stored = localStorage.getItem(STORAGE_KEY);
    selectedCity.value = stored || DEFAULT_CITY;
    cityInput.value = stored || DEFAULT_CITY;
  } catch {
    selectedCity.value = DEFAULT_CITY;
    cityInput.value = DEFAULT_CITY;
  }
}

function saveCity(city: string) {
  try {
    localStorage.setItem(STORAGE_KEY, city);
  } catch {
    // ignore
  }
  selectedCity.value = city;
  cityInput.value = city;
}

function updateClock() {
  const now = new Date();
  clockTime.value = now.toLocaleTimeString("it-IT", {
    hour: "2-digit",
    minute: "2-digit",
  });
}

async function geocodeCity(city: string) {
  const data = await apiGet<{ lat: number; lon: number; city: string }>(
    "/api/v1/weather/geocode",
    { city },
    { timeoutMs: 10000, noRetry: true },
  );
  return data;
}

async function fetchWeather(lat: number, lon: number) {
  loading.value = true;
  weatherError.value = "";
  try {
    const params: Record<string, string> = {
      lat: String(lat),
      lon: String(lon),
    };
    const data = await apiGet("/api/v1/weather", params);
    weather.value = data as Record<string, unknown>;
  } catch (e: unknown) {
    weatherError.value = e instanceof Error ? e.message : "Errore meteo";
    weather.value = null;
  } finally {
    loading.value = false;
  }
}

async function resolveAndFetch(city: string) {
  saveCity(city);
  menuOpen.value = false;
  loading.value = true;
  weatherError.value = "";
  try {
    const geo = await geocodeCity(city);
    await fetchWeather(geo.lat, geo.lon);
  } catch (e: unknown) {
    weatherError.value =
      e instanceof Error ? e.message : "Localita non trovata";
    weather.value = null;
  } finally {
    loading.value = false;
  }
}

async function onCitySubmit() {
  const city = cityInput.value.trim();
  if (!city) return;
  await resolveAndFetch(city);
}

async function onGps() {
  if (!navigator.geolocation) {
    weatherError.value = "GPS non supportato";
    return;
  }
  loading.value = true;
  weatherError.value = "";
  try {
    const pos = await new Promise<GeolocationPosition>((resolve, reject) => {
      navigator.geolocation.getCurrentPosition(resolve, reject, {
        enableHighAccuracy: true,
        timeout: 10000,
        maximumAge: 60000,
      });
    });
    const { latitude, longitude } = pos.coords;
    const gpsLabel = `GPS ${latitude.toFixed(2)}, ${longitude.toFixed(2)}`;
    cityInput.value = gpsLabel;
    saveCity(gpsLabel);
    menuOpen.value = false;
    await fetchWeather(latitude, longitude);
  } catch (e: unknown) {
    weatherError.value = e instanceof Error ? e.message : "Errore GPS";
    weather.value = null;
  } finally {
    loading.value = false;
  }
}

function toggleMenu() {
  menuOpen.value = !menuOpen.value;
}

function onDocClick(e: MouseEvent) {
  const target = e.target as HTMLElement;
  if (!target.closest(".wcw")) {
    menuOpen.value = false;
  }
}

function weatherIconFor(desc?: string): string {
  const d = (desc || "").toLowerCase();
  if (d.includes("nuvol") || d.includes("nub") || d.includes("cloud"))
    return "☁️";
  if (d.includes("pioggia") || d.includes("rain") || d.includes("shower"))
    return "🌧️";
  if (d.includes("temporale") || d.includes("storm") || d.includes("thunder"))
    return "⛈️";
  if (d.includes("neve") || d.includes("snow") || d.includes("sleet"))
    return "❄️";
  if (d.includes("nebbia") || d.includes("fog") || d.includes("mist"))
    return "🌫️";
  if (d.includes("sereno") || d.includes("clear")) return "☀️";
  if (d.includes("sole") || d.includes("sun")) return "🌤️";
  if (d.includes("rovesc")) return "🌦️";
  return "🌡️";
}

const computedWeatherIcon = computed(() => {
  if (!weather.value) return "🌡️";
  const desc = (weather.value.description as string) || "";
  return weatherIconFor(desc);
});

const computedTemperature = computed(() => {
  if (!weather.value) return 0;
  const t = weather.value.temperature;
  return typeof t === "number" ? t : Number(t ?? 0);
});

onMounted(async () => {
  loadCity();
  updateClock();
  clockTimer = window.setInterval(updateClock, 10000);
  document.addEventListener("click", onDocClick);
  try {
    const stored = selectedCity.value;
    if (stored.startsWith("GPS ")) {
      const parts = stored.replace("GPS ", "").split(",").map(Number);
      if (parts.length === 2 && !parts.some(isNaN)) {
        await fetchWeather(parts[0], parts[1]);
      }
    } else if (stored) {
      const geo = await geocodeCity(stored);
      await fetchWeather(geo.lat, geo.lon);
    }
  } catch {
    // silent on initial load
  }
});

onUnmounted(() => {
  if (clockTimer) window.clearInterval(clockTimer);
  document.removeEventListener("click", onDocClick);
});
</script>

<style scoped>
.wcw {
  position: relative;
  display: inline-flex;
  align-items: center;
  gap: 6px;
  font-size: 0.85rem;
  color: var(--text-primary);
}

.wcw-main {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 6px 10px;
  border-radius: var(--radius-sm);
  border: 1px solid var(--border);
  background: var(--bg-secondary);
  backdrop-filter: blur(var(--glass-blur));
  -webkit-backdrop-filter: blur(var(--glass-blur));
  cursor: pointer;
  transition: var(--transition);
  white-space: nowrap;
}

.wcw-main:hover {
  border-color: var(--border-light);
  box-shadow: var(--glow-soft);
}

.wcw-clock {
  font-family: "Outfit", sans-serif;
  font-weight: 700;
  font-size: 0.9rem;
  color: var(--accent);
  min-width: 52px;
  text-align: center;
}

.wcw-weather {
  display: inline-flex;
  align-items: center;
  gap: 4px;
}

.wcw-weather--empty {
  color: var(--text-muted);
}

.wcw-icon {
  font-size: 1rem;
}

.wcw-temp {
  font-weight: 600;
  font-family: "Outfit", sans-serif;
}

.wcw-chevron {
  font-size: 0.7rem;
  color: var(--text-muted);
  transition: transform 0.2s;
}

.wcw-chevron--open {
  transform: rotate(180deg);
}

.wcw-menu {
  position: absolute;
  top: calc(100% + 8px);
  right: 0;
  z-index: 50;
  background: var(--bg-secondary);
  border: 1px solid var(--border);
  border-radius: var(--radius-sm);
  padding: 12px;
  display: flex;
  flex-direction: column;
  gap: 8px;
  min-width: 220px;
  box-shadow: var(--shadow-lg);
  backdrop-filter: blur(var(--glass-blur));
  -webkit-backdrop-filter: blur(var(--glass-blur));
}

.wcw-city-row {
  display: flex;
  gap: 6px;
}

.wcw-city-row input {
  flex: 1;
  padding: 6px 8px;
  border-radius: var(--radius-sm);
  border: 1px solid var(--border);
  background: var(--bg-primary);
  color: var(--text-primary);
  font-size: 0.85rem;
  outline: none;
}

.wcw-city-row input:focus {
  border-color: var(--accent);
}

.wcw-btn {
  padding: 6px 10px;
  border-radius: var(--radius-sm);
  border: 1px solid var(--border);
  background: var(--bg-tertiary);
  color: var(--text-primary);
  cursor: pointer;
  font-size: 0.8rem;
  font-weight: 600;
  transition: var(--transition);
}

.wcw-btn--primary {
  background: var(--accent);
  color: #000;
  border-color: var(--accent);
}

.wcw-btn--primary:hover {
  opacity: 0.9;
}

.wcw-btn--gps {
  background: transparent;
  border-color: var(--border);
}

.wcw-btn--gps:hover {
  border-color: var(--accent);
  color: var(--accent);
}

.wcw-error {
  color: var(--error);
  font-size: 0.75rem;
  margin-top: 4px;
}

@media (max-width: 768px) {
  .wcw-clock {
    font-size: 0.8rem;
    min-width: 44px;
  }

  .wcw-temp {
    font-size: 0.8rem;
  }

  .wcw-main {
    padding: 5px 8px;
    gap: 6px;
  }
}
</style>
