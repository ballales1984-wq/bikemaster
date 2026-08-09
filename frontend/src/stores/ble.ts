/**
 * BikeMaster Frontend — store gestione dispositivi BLE.
 *
 * Gestisce la scansione, la registrazione, la connessione e la sincronizzazione
 * di dispositivi Bluetooth Low Energy (bilance, cardio, ecc.) tramite
 * Web Bluetooth API.
 */

import { defineStore } from "pinia";
import { ref } from "vue";
import type { ApiCallOptions } from "../utils/api";
import { apiGet, apiPost, apiPut, apiDelete } from "../utils/api";
import { useAuthStore } from "./auth";
import { isTauri } from "../utils/backend-config";

export type BleDeviceType =
  "weight_scale" | "heart_rate" | "blood_pressure" | "thermometer" | "generic";

export interface BleDevice {
  id: number;
  athlete_id: number;
  tenant_id: number;
  device_id: string;
  name: string;
  device_type: BleDeviceType;
  service_uuid: string | null;
  characteristic_uuid: string | null;
  mac_address: string | null;
  paired: boolean;
  last_connected_at: string | null;
  last_synced_at: string | null;
  settings: string;
  created_at: string | null;
  updated_at: string | null;
}

export const useBleStore = defineStore("ble", () => {
  const auth = useAuthStore();
  const devices = ref<BleDevice[]>([]);
  const loading = ref(false);
  const scanning = ref(false);
  const error = ref("");

  const knownServices: Record<
    BleDeviceType,
    { service: string; characteristic: string; label: string }
  > = {
    weight_scale: {
      service: "0000181d-0000-1000-8000-00805f9b34fb",
      characteristic: "00002a9d-0000-1000-8000-00805f9b34fb",
      label: "Bilancia",
    },
    heart_rate: {
      service: "0000180d-0000-1000-8000-00805f9b34fb",
      characteristic: "00002a37-0000-1000-8000-00805f9b34fb",
      label: "Cardio",
    },
    blood_pressure: {
      service: "00001810-0000-1000-8000-00805f9b34fb",
      characteristic: "00002a35-0000-1000-8000-00805f9b34fb",
      label: "Misuratore pressione",
    },
    thermometer: {
      service: "00001809-0000-1000-8000-00805f9b34fb",
      characteristic: "00002a1c-0000-1000-8000-00805f9b34fb",
      label: "Termometro",
    },
    generic: {
      service: "",
      characteristic: "",
      label: "Generico",
    },
  };

  const BLE_DEVICE_ID_MAP_KEY = "bikemaster_ble_device_id_map";

  function stableDeviceIdentity(
    name: string,
    serviceUuid: string | null,
  ): string {
    return `${(name || "unknown").toLowerCase()}|${serviceUuid || "none"}`;
  }

  function loadBleDeviceIdMap(): Record<string, string> {
    try {
      const raw = localStorage.getItem(BLE_DEVICE_ID_MAP_KEY);
      return raw ? JSON.parse(raw) : {};
    } catch {
      return {};
    }
  }

  function saveBleDeviceIdMap(map: Record<string, string>) {
    try {
      localStorage.setItem(BLE_DEVICE_ID_MAP_KEY, JSON.stringify(map));
    } catch {
      // ignore storage errors
    }
  }

  function findRegisteredDeviceByIdentity(
    devicesList: BleDevice[],
    name: string,
    serviceUuid: string | null,
  ): BleDevice | undefined {
    const identity = stableDeviceIdentity(name, serviceUuid);
    return devicesList.find((d) => {
      const devUuid = d.service_uuid || null;
      return stableDeviceIdentity(d.name, devUuid) === identity;
    });
  }

  async function load() {
    loading.value = true;
    error.value = "";
    try {
      const token = auth.token;
      const headers = token ? { Authorization: `Bearer ${token}` } : {};
      const data = await apiGet<{ devices: BleDevice[] }>(
        "/api/v1/ble/devices",
        {},
        { headers } as ApiCallOptions,
      );
      devices.value = data.devices || [];
    } catch (e) {
      error.value =
        e instanceof Error
          ? e.message
          : "Impossibile caricare i dispositivi BLE";
    } finally {
      loading.value = false;
    }
  }

  async function register(device: {
    device_id: string;
    name: string;
    device_type: BleDeviceType;
    service_uuid?: string;
    characteristic_uuid?: string;
    mac_address?: string;
  }) {
    loading.value = true;
    error.value = "";
    try {
      const token = auth.token;
      const headers = token ? { Authorization: `Bearer ${token}` } : {};
      const resp = await apiPost<{
        id: number;
        device_id: string;
        name: string;
      }>(
        "/api/v1/ble/devices",
        {
          ...device,
          service_uuid:
            device.service_uuid ||
            knownServices[device.device_type].service ||
            null,
          characteristic_uuid:
            device.characteristic_uuid ||
            knownServices[device.device_type].characteristic ||
            null,
        },
        { headers } as ApiCallOptions,
      );
      await load();
      return resp;
    } catch (e) {
      error.value =
        e instanceof Error ? e.message : "Registrazione dispositivo fallita";
      throw e;
    } finally {
      loading.value = false;
    }
  }

  async function update(
    deviceId: number,
    updates: { name?: string; paired?: boolean; settings?: string },
  ) {
    loading.value = true;
    error.value = "";
    try {
      const token = auth.token;
      const headers = token ? { Authorization: `Bearer ${token}` } : {};
      const resp = await apiPut<BleDevice>(
        `/api/v1/ble/devices/${deviceId}`,
        updates,
        { headers } as ApiCallOptions,
      );
      await load();
      return resp;
    } catch (e) {
      error.value =
        e instanceof Error ? e.message : "Aggiornamento dispositivo fallito";
      throw e;
    } finally {
      loading.value = false;
    }
  }

  async function unregister(deviceId: number) {
    loading.value = true;
    error.value = "";
    try {
      const token = auth.token;
      const headers = token ? { Authorization: `Bearer ${token}` } : {};
      await apiDelete(`/api/v1/ble/devices/${deviceId}`, {
        headers,
      } as ApiCallOptions);
      await load();
    } catch (e) {
      error.value =
        e instanceof Error ? e.message : "Rimozione dispositivo fallita";
      throw e;
    } finally {
      loading.value = false;
    }
  }

  async function sync(deviceId: number) {
    loading.value = true;
    error.value = "";
    try {
      const token = auth.token;
      const headers = token ? { Authorization: `Bearer ${token}` } : {};
      const device = devices.value.find((d) => d.id === deviceId);
      const syncPayload: Record<string, unknown> = {};
      if (device && device.service_uuid && device.characteristic_uuid) {
        const measurement = await readBleMeasurement(device);
        if (measurement !== null) {
          syncPayload.value = measurement.value;
          syncPayload.unit = measurement.unit;
          syncPayload.recorded_at = new Date().toISOString();
        }
      }
      await apiPost(`/api/v1/ble/devices/${deviceId}/sync`, syncPayload, {
        headers,
      } as ApiCallOptions);
      await load();
    } catch (e) {
      error.value =
        e instanceof Error ? e.message : "Sincronizzazione dispositivo fallita";
      throw e;
    } finally {
      loading.value = false;
    }
  }

  type BleDataView = DataView;
  interface BleCharacteristic {
    readValue: () => Promise<BleDataView>;
  }
  interface BleService {
    getCharacteristic: (uuid: string) => Promise<BleCharacteristic>;
  }
  interface BleGatt {
    connect: () => Promise<BleServer>;
    disconnect: () => void;
  }
  interface BleServer {
    getPrimaryService: (uuid: string) => Promise<BleService>;
    disconnect: () => void;
  }
  interface BleWebDevice {
    id: string;
    name?: string;
    gatt?: BleGatt;
  }
  interface BleNavigator {
    bluetooth?: {
      requestDevice: (opts: Record<string, unknown>) => Promise<BleWebDevice>;
      getDevices?: () => Promise<BleWebDevice[]>;
    };
  }

  function parseSfloat(view: DataView, offset: number): number {
    const raw = view.getUint16(offset, true);
    let mantissa = raw & 0x0fff;
    let exponent = (raw >> 12) & 0x000f;
    if (exponent >= 8) exponent -= 16;
    if (mantissa >= 2048) mantissa -= 4096;
    return mantissa * Math.pow(10, exponent);
  }

  function parseBleCharacteristic(
    deviceType: BleDeviceType,
    view: DataView,
  ): { value: number; unit: string } | null {
    if (view.byteLength < 2) return null;
    const flags = view.getUint8(0);
    if (deviceType === "heart_rate") {
      const isUint16 = flags & 0x01;
      const hr = isUint16 ? view.getUint16(1, true) : view.getUint8(1);
      return { value: hr, unit: "bpm" };
    }
    if (deviceType === "weight_scale") {
      const isImperial = flags & 0x01;
      const raw = view.getUint16(1, true);
      if (isImperial) {
        return { value: raw / 100, unit: "lb" };
      }
      return { value: raw / 200, unit: "kg" };
    }
    if (deviceType === "blood_pressure") {
      const systolic = parseSfloat(view, 1);
      if (isNaN(systolic)) return null;
      return { value: systolic, unit: "mmHg" };
    }
    if (deviceType === "thermometer") {
      const isFahrenheit = flags & 0x01;
      const tempC = parseSfloat(view, 1);
      if (isNaN(tempC)) return null;
      const value = isFahrenheit ? (tempC * 5) / 9 + 32 : tempC;
      return { value, unit: isFahrenheit ? "°F" : "°C" };
    }
    const raw = view.getUint8(1);
    return { value: raw, unit: "value" };
  }

  async function readBleMeasurementTauri(
    device: BleDevice,
  ): Promise<{ value: number; unit: string } | null> {
    const macAddress = device.mac_address || device.device_id;
    const core = await import("@tauri-apps/api/core");
    const result = (await core.invoke("ble_read_measurement", {
      mac_address: macAddress,
      service_uuid: device.service_uuid,
      characteristic_uuid: device.characteristic_uuid,
      device_type: device.device_type,
    })) as { value?: number; unit?: string; raw?: number[] };
    if (result.value !== undefined && result.unit !== undefined) {
      return { value: result.value, unit: result.unit };
    }
    if (result.raw) {
      const bytes = new Uint8Array(result.raw).buffer;
      const view = new DataView(bytes);
      return parseBleCharacteristic(device.device_type, view);
    }
    return null;
  }

  async function readBleMeasurement(
    device: BleDevice,
  ): Promise<{ value: number; unit: string } | null> {
    if (isTauri()) {
      return readBleMeasurementTauri(device);
    }
    const btNavigator = navigator as unknown as BleNavigator;
    if (!btNavigator.bluetooth) {
      throw new Error("Web Bluetooth non disponibile");
    }
    let bleDevice: BleWebDevice | undefined;
    if (typeof btNavigator.bluetooth.getDevices === "function") {
      const devices = await btNavigator.bluetooth.getDevices();
      bleDevice = devices.find((d) => d.id === device.device_id);
    }
    if (!bleDevice) {
      bleDevice = await btNavigator.bluetooth.requestDevice({
        filters: [{ services: [device.service_uuid] }],
        optionalServices: [device.service_uuid!],
      });
    }
    const gatt = bleDevice.gatt;
    if (!gatt) throw new Error("Connessione GATT non disponibile");
    const server = await gatt.connect();
    try {
      const service = await server.getPrimaryService(device.service_uuid!);
      const characteristic = await service.getCharacteristic(
        device.characteristic_uuid!,
      );
      const value = await characteristic.readValue();
      return parseBleCharacteristic(device.device_type, value);
    } finally {
      server.disconnect();
    }
  }

  async function scanForDevicesTauri(): Promise<
    Array<{
      deviceId: string;
      name: string;
      type: BleDeviceType;
      service_uuid?: string;
      is_known?: boolean;
    }>
  > {
    scanning.value = true;
    error.value = "";
    try {
      const core = await import("@tauri-apps/api/core");
      const devices: Array<{
        device_id: string;
        name: string;
        device_type: string;
        service_uuid: string;
      }> = await core.invoke("ble_scan");
      const map = loadBleDeviceIdMap();
      const result = devices.map((d) => {
        const serviceUuid = d.service_uuid || null;
        const identity = stableDeviceIdentity(d.name, serviceUuid);
        const mappedDeviceId = map[identity];
        const item = {
          deviceId: mappedDeviceId || d.device_id,
          name: d.name,
          type: (d.device_type as BleDeviceType) || "generic",
          service_uuid: serviceUuid || undefined,
          is_known: !!mappedDeviceId,
        };
        map[identity] = item.deviceId;
        return item;
      });
      saveBleDeviceIdMap(map);
      return result;
    } catch (e) {
      error.value = e instanceof Error ? e.message : "Scansione BLE fallita";
      throw e;
    } finally {
      scanning.value = false;
    }
  }

  async function scanForDevices(): Promise<
    Array<{
      deviceId: string;
      name: string;
      type: BleDeviceType;
      service_uuid?: string;
      is_known?: boolean;
    }>
  > {
    if (isTauri()) {
      return scanForDevicesTauri();
    }
    if (!("bluetooth" in navigator)) {
      throw new Error("Web Bluetooth non supportato in questo browser");
    }
    scanning.value = true;
    error.value = "";
    const found: Array<{
      deviceId: string;
      name: string;
      type: BleDeviceType;
      service_uuid?: string;
      is_known?: boolean;
    }> = [];
    try {
      type BleRequestDeviceFn = (opts: Record<string, unknown>) => Promise<{
        id: string;
        name?: string;
        gatt?: { connect: () => Promise<unknown>; disconnect: () => void };
      }>;
      const btNavigator = navigator as unknown as {
        bluetooth?: {
          requestDevice: BleRequestDeviceFn;
        };
      };
      if (!btNavigator.bluetooth) {
        throw new Error("Web Bluetooth non disponibile");
      }
      const optionalServices = Object.values(knownServices)
        .map((s) => s.service)
        .filter((uuid): uuid is string => !!uuid);
      const device = await btNavigator.bluetooth.requestDevice({
        acceptAllDevices: true,
        optionalServices,
      });

      let detectedType: BleDeviceType = "generic";
      try {
        if (device.gatt?.connect) {
          const server = (await device.gatt.connect()) as {
            getPrimaryService: (uuid: string) => Promise<unknown>;
          };
          for (const [type, info] of Object.entries(knownServices)) {
            if (!info.service) continue;
            try {
              await server.getPrimaryService(info.service);
              detectedType = type as BleDeviceType;
              break;
            } catch {
              // continue searching
            }
          }
          try {
            device.gatt.disconnect();
          } catch {
            // ignore disconnect errors
          }
        }
      } catch {
        // service discovery failed, keep generic
      }

      const serviceUuid =
        detectedType !== "generic" ? knownServices[detectedType].service : null;
      const identity = stableDeviceIdentity(
        device.name || "Dispositivo sconosciuto",
        serviceUuid,
      );
      const map = loadBleDeviceIdMap();
      const mappedDeviceId = map[identity];

      found.push({
        deviceId: mappedDeviceId || device.id || crypto.randomUUID(),
        name: device.name || "Dispositivo sconosciuto",
        type: detectedType,
        service_uuid: serviceUuid || undefined,
        is_known: !!mappedDeviceId,
      });

      map[identity] = found[found.length - 1].deviceId;
      saveBleDeviceIdMap(map);
    } catch (e) {
      if ((e as Error).name !== "NotFoundError") {
        throw e;
      }
    } finally {
      scanning.value = false;
    }
    return found;
  }

  function getDeviceTypeLabel(type: BleDeviceType): string {
    return knownServices[type]?.label || type;
  }

  return {
    devices,
    loading,
    scanning,
    error,
    knownServices,
    load,
    register,
    update,
    unregister,
    sync,
    scanForDevices,
    getDeviceTypeLabel,
    findRegisteredDeviceByIdentity,
  };
});
