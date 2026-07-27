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
      await apiPost(`/api/v1/ble/devices/${deviceId}/sync`, {}, {
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

  async function scanForDevices(): Promise<
    Array<{ deviceId: string; name: string; type: BleDeviceType }>
  > {
    if (!("bluetooth" in navigator)) {
      throw new Error("Web Bluetooth non supportato in questo browser");
    }
    scanning.value = true;
    error.value = "";
    const found: Array<{
      deviceId: string;
      name: string;
      type: BleDeviceType;
    }> = [];
    try {
      type BleRequestDeviceFn = (
        opts: Record<string, unknown>,
      ) => Promise<{ id: string; name?: string }>;
      const btNavigator = navigator as unknown as {
        bluetooth?: {
          requestDevice: BleRequestDeviceFn;
        };
      };
      if (!btNavigator.bluetooth) {
        throw new Error("Web Bluetooth non disponibile");
      }
      const device = await btNavigator.bluetooth.requestDevice({
        acceptAllDevices: true,
        optionalServices: [
          "0000181d-0000-1000-8000-00805f9b34fb",
          "0000180d-0000-1000-8000-00805f9b34fb",
        ],
      });
      found.push({
        deviceId: device.id || crypto.randomUUID(),
        name: device.name || "Dispositivo sconosciuto",
        type: "generic",
      });
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
  };
});
