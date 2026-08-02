/**
 * Composable per il tracciamento continuo della frequenza cardiaca 24h.
 *
 * Gestisce l'acquisizione di dati HR da:
 * - Dispositivi BLE via Web Bluetooth (browser): sottoscrizione a notifiche.
 * - Tauri desktop/mobile: comando BLE nativo con polling a intervalli
 *   configurabili o notifiche via eventi Tauri.
 *
 * I campioni vengono batchati e persistiti periodicamente sul backend
 * tramite il store Pinia `useHr24hStore`, eliminando la dipendenza da
 * Google Health / Google Fit.
 */

import { ref, onUnmounted } from "vue";
import { isTauri } from "../utils/backend-config";
import { useHr24hStore } from "../stores/hr24h";
import type { Hr24hSample } from "../types";

const HEART_RATE_SERVICE_UUID = "0000180d-0000-1000-8000-00805f9b34fb";
const HEART_RATE_CHARACTERISTIC_UUID = "00002a37-0000-1000-8000-00805f9b34fb";

interface BleCharacteristic {
  readValue: () => Promise<DataView>;
  startNotifications?: () => Promise<void>;
  stopNotifications?: () => Promise<void>;
  onCharacteristicsValueChanged?: (cb: (value: DataView) => void) => void;
}

interface BleService {
  getCharacteristic: (uuid: string) => Promise<BleCharacteristic>;
}

interface BleServer {
  getPrimaryService: (uuid: string) => Promise<BleService>;
  disconnect: () => void;
}

interface BleWebDevice {
  id: string;
  name?: string;
  gatt?: {
    connect: () => Promise<BleServer>;
    disconnect: () => void;
  };
}

interface BleNavigator {
  bluetooth?: {
    requestDevice: (opts: Record<string, unknown>) => Promise<BleWebDevice>;
    getDevices?: () => Promise<BleWebDevice[]>;
  };
}

function parseHeartRateFromBytes(data: DataView): number | null {
  if (data.byteLength < 2) return null;
  const flags = data.getUint8(0);
  const isUint16 = flags & 0x01;
  const hr = isUint16 ? data.getUint16(1, true) : data.getUint8(1);
  if (hr < 0 || hr > 300) return null;
  return hr;
}

export function useHr24h() {
  const store = useHr24hStore();
  const isRunning = ref(false);
  const isConnected = ref(false);
  const deviceLabel = ref<string | null>(null);
  const error = ref<string | null>(null);
  const sampleCount = ref(0);

  let _webTimer: number | null = null;
  let _batch: Hr24hSample[] = [];
  let _polling = false;

  function enqueueSample(hr: number) {
    const ts = new Date().toISOString();
    const sample: Hr24hSample = {
      id: 0,
      heart_rate: hr,
      source: store.settings.source || "ble",
      device_id: store.settings.device_id,
      recorded_at: ts,
    };
    store.samples.push(sample);
    _batch.push(sample);
    sampleCount.value += 1;
    store.isCollecting = true;

    store.samples = store.samples.slice(-1000);

    const flushThreshold = Math.max(store.settings.interval_seconds * 2, 30);
    if (_batch.length >= flushThreshold) {
      void flushBatch();
    }
  }

  async function flushBatch() {
    if (_batch.length === 0) return;
    const toFlush = _batch.splice(0);
    await store.logSamples(toFlush);
  }

  /* ---- Web Bluetooth path (browser) ---- */

  async function startWebBluetooth(deviceId?: string) {
    const btNavigator = navigator as unknown as BleNavigator;
    if (!btNavigator.bluetooth) {
      throw new Error(
        "Web Bluetooth non disponibile. Usa l'app Tauri desktop.",
      );
    }

    const filters = [{ services: [HEART_RATE_SERVICE_UUID] }];
    const optionalServices = [HEART_RATE_SERVICE_UUID];
    const bluetooth = btNavigator.bluetooth;
    const device = deviceId
      ? bluetooth.getDevices
        ? await bluetooth
            .getDevices()
            .then((devices) => devices.find((d) => d.id === deviceId))
            .catch(() => undefined)
        : undefined
      : undefined;

    let bleDevice: BleWebDevice;
    if (device && device.gatt) {
      bleDevice = device;
    } else {
      bleDevice = await btNavigator.bluetooth.requestDevice({
        filters,
        optionalServices,
      });
    }

    deviceLabel.value = bleDevice.name || "Cardiofischia BLE";
    isConnected.value = true;

    const gatt = bleDevice.gatt;
    if (!gatt) {
      throw new Error("GATT non disponibile sul dispositivo BLE");
    }
    const server = await gatt.connect();
    const service = await server.getPrimaryService(HEART_RATE_SERVICE_UUID);
    const characteristic = await service.getCharacteristic(
      HEART_RATE_CHARACTERISTIC_UUID,
    );

    if (
      characteristic.startNotifications &&
      characteristic.onCharacteristicsValueChanged
    ) {
      characteristic.onCharacteristicsValueChanged((value: DataView) => {
        const hr = parseHeartRateFromBytes(value);
        if (hr !== null) {
          enqueueSample(hr);
        }
      });
      await characteristic.startNotifications();
    } else {
      void pollCharacteristic(characteristic);
    }
  }

  async function pollCharacteristic(characteristic: BleCharacteristic) {
    _polling = true;
    while (_polling && isRunning.value) {
      try {
        const value = await characteristic.readValue();
        const hr = parseHeartRateFromBytes(value);
        if (hr !== null) {
          enqueueSample(hr);
        }
      } catch (e) {
        error.value = e instanceof Error ? e.message : "Errore lettura BLE";
      }
      const interval = store.settings.interval_seconds * 1000;
      await new Promise((resolve) => setTimeout(resolve, interval));
    }
  }

  /* ---- Tauri path (desktop / mobile) ---- */

  async function startTauriMonitoring() {
    const core = await import("@tauri-apps/api/core");
    const { listen } = await import("@tauri-apps/api/event");

    const device = store.settings.device_id || "";
    if (!device) {
      throw new Error(
        "Nessun dispositivo BLE configurato. Configuralo in Impostazioni > Connessioni.",
      );
    }

    const deviceInfo = await core
      .invoke<{
        service_uuid: string;
        characteristic_uuid: string;
        mac_address: string;
      }>("ble_get_device_info", { device_id: device })
      .catch(() => ({
        service_uuid: HEART_RATE_SERVICE_UUID,
        characteristic_uuid: HEART_RATE_CHARACTERISTIC_UUID,
        mac_address: device,
      }));

    await core.invoke("ble_start_hr_monitoring", {
      mac_address: deviceInfo.mac_address,
      service_uuid: deviceInfo.service_uuid || HEART_RATE_SERVICE_UUID,
      characteristic_uuid:
        deviceInfo.characteristic_uuid || HEART_RATE_CHARACTERISTIC_UUID,
    });

    deviceLabel.value = device;
    isConnected.value = true;

    const unlisten = await listen("hr-sample", (event) => {
      const payload = event.payload as {
        heart_rate: number;
        timestamp: string;
      };
      if (payload && payload.heart_rate) {
        enqueueSample(payload.heart_rate);
      }
    });

    return () => unlisten();
  }

  async function stopTauriMonitoring() {
    const core = await import("@tauri-apps/api/core");
    if (store.settings.device_id) {
      await core.invoke("ble_stop_hr_monitoring", {
        mac_address: store.settings.device_id,
      });
    }
  }

  /* ---- Public API ---- */

  async function start(deviceId?: string) {
    if (isRunning.value) return;
    isRunning.value = true;
    error.value = null;
    _batch = [];

    try {
      if (!store.settings.enabled) {
        await store.saveSettings({ enabled: true });
      }

      if (isTauri()) {
        await startTauriMonitoring();
      } else {
        await startWebBluetooth(deviceId);
      }
    } catch (e) {
      error.value =
        e instanceof Error ? e.message : "Errore avvio tracciamento HR";
      isRunning.value = false;
      isConnected.value = false;
      throw e;
    }
  }

  async function stop() {
    isRunning.value = false;
    _polling = false;

    if (isTauri()) {
      await stopTauriMonitoring();
    }

    isConnected.value = false;
    deviceLabel.value = null;
    await flushBatch();
  }

  async function refresh24h() {
    await store.load24h();
  }

  async function refreshSummary() {
    await store.loadTodaySummary();
    await store.loadDailyHistory();
  }

  onUnmounted(() => {
    void stop();
  });

  return {
    isRunning,
    isConnected,
    deviceLabel,
    error,
    sampleCount,
    start,
    stop,
    refresh24h,
    refreshSummary,
    parseHeartRateFromBytes,
  };
}
