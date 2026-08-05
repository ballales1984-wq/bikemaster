/**
 * Voice command registry and parser.
 *
 * Defines all supported voice commands organized by domain,
 * and provides a parser that maps transcripts to commands
 * with extracted parameters.
 */

import type {
  VoiceCommandDefinition,
  VoiceCommandParameter,
  VoiceCommandResult,
  ParsedCommand,
  VoiceCommandLogEntry,
} from "../types/voiceCommands";
import { useRidesStore } from "../stores/rides";
import { useAthleteStore } from "../stores/athlete";
import { useUIStore } from "../stores/ui";
import { useMetabolismStore } from "../stores/metabolism";
import type { FoodLog, CalendarEvent } from "../types/index";
import router from "../router/index";

function buildResult(
  success: boolean,
  message: string,
  data?: unknown,
): VoiceCommandResult {
  return { success, message, data };
}

function requireParam(params: Record<string, unknown>, name: string): unknown {
  const v = params[name];
  if (v === undefined || v === null || v === "") {
    throw new Error(`Parametro mancante: ${name}`);
  }
  return v;
}

function getMealLabel(mealType: FoodLog["meal_type"]): string {
  const map: Record<string, string> = {
    breakfast: "Colazione",
    lunch: "Pranzo",
    dinner: "Cena",
    snack: "Spuntino",
    other: "Pasto",
  };
  return map[mealType] || "Pasto";
}

function estimateKcal(description: string): number {
  const lower = description.toLowerCase();
  if (lower.includes("pasta") && lower.includes("ragu")) return 450;
  if (lower.includes("pasta")) return 350;
  if (lower.includes("risotto")) return 400;
  if (lower.includes("pizza")) return 800;
  if (lower.includes("insalata")) return 150;
  if (lower.includes("carne")) return 400;
  if (lower.includes("pollo")) return 300;
  if (lower.includes("pesce")) return 250;
  if (lower.includes("uova")) return 200;
  if (lower.includes("formaggio")) return 300;
  if (lower.includes("frutta")) return 100;
  if (lower.includes("yogurt")) return 150;
  if (lower.includes("cappuccino")) return 150;
  if (lower.includes("cornetto")) return 250;
  if (lower.includes("panino")) return 350;
  if (lower.includes("hamburger")) return 500;
  return 0;
}

function parseItalianDate(text: string): string | null {
  const months: Record<string, number> = {
    gennaio: 0,
    febbrio: 1,
    marzo: 2,
    aprile: 3,
    maggio: 4,
    giugno: 5,
    luglio: 6,
    agosto: 7,
    settembre: 8,
    ottobre: 9,
    novembre: 10,
    dicembre: 11,
    gen: 0,
    feb: 1,
    mar: 2,
    apr: 3,
    mag: 4,
    giu: 5,
    lug: 6,
    ago: 7,
    set: 8,
    ott: 9,
    nov: 10,
    dic: 11,
  };

  const today = new Date();
  const lower = text.toLowerCase();

  if (lower.includes("oggi") || lower.includes("stasera")) {
    return today.toISOString().split("T")[0];
  }
  if (lower.includes("domani")) {
    const d = new Date(today);
    d.setDate(d.getDate() + 1);
    return d.toISOString().split("T")[0];
  }
  if (lower.includes("dopodomani")) {
    const d = new Date(today);
    d.setDate(d.getDate() + 2);
    return d.toISOString().split("T")[0];
  }

  const dayMatch = lower.match(
    /(\d{1,2})\s*(ottobre|novembre|dicembre|gennaio|febbraio|marzo|aprile|maggio|giugno|luglio|agosto|settembre)/,
  );
  if (dayMatch) {
    const day = parseInt(dayMatch[1], 10);
    const month = months[dayMatch[2]];
    if (!isNaN(day) && month !== undefined) {
      const d = new Date(today.getFullYear(), month, day);
      return d.toISOString().split("T")[0];
    }
  }

  return null;
}

function parseTime(text: string): string | null {
  const timeMatch = text.match(
    /(\d{1,2})[.:](\d{2})\s*(?:di sera|di mattina|del mattino|del pomeriggio|di pomeriggio|del pomeriggio)?/i,
  );
  if (timeMatch) {
    let hours = parseInt(timeMatch[1], 10);
    const minutes = parseInt(timeMatch[2], 10);
    const suffix = (timeMatch[3] || "").toLowerCase();
    if (
      (suffix.includes("sera") || suffix.includes("pomeriggio")) &&
      hours < 12
    ) {
      hours += 12;
    }
    if (hours >= 0 && hours <= 23 && minutes >= 0 && minutes <= 59) {
      return `${String(hours).padStart(2, "0")}:${String(minutes).padStart(2, "0")}`;
    }
  }
  const simpleHour = text.match(
    /(\d{1,2})\s*(?:di sera|di mattina|del mattino|del pomeriggio|di pomeriggio|del pomeriggio)?/i,
  );
  if (simpleHour) {
    let hours = parseInt(simpleHour[1], 10);
    const suffix = (simpleHour[2] || "").toLowerCase();
    if (
      (suffix.includes("sera") || suffix.includes("pomeriggio")) &&
      hours < 12
    ) {
      hours += 12;
    }
    if (hours >= 0 && hours <= 23) {
      return `${String(hours).padStart(2, "0")}:00`;
    }
  }
  return null;
}

function parseNumber(text: string): number | null {
  const cleaned = text.replace(/[^\d.,]/g, "").replace(",", ".");
  const n = parseFloat(cleaned);
  return isNaN(n) ? null : n;
}

function parseMealType(text: string): FoodLog["meal_type"] | null {
  const lower = text.toLowerCase();
  if (lower.includes("colazione")) return "breakfast";
  if (lower.includes("pranzo")) return "lunch";
  if (lower.includes("cena")) return "dinner";
  if (lower.includes("spuntino") || lower.includes("snack")) return "snack";
  return null;
}

function parseEventType(text: string): CalendarEvent["event_type"] | null {
  const lower = text.toLowerCase();
  if (lower.includes("gara") || lower.includes("race")) return "race";
  if (lower.includes("recupero") || lower.includes("recovery"))
    return "recovery";
  if (lower.includes("test")) return "test";
  if (
    lower.includes("allenamento") ||
    lower.includes("training") ||
    lower.includes("ride")
  )
    return "training";
  return null;
}

export function createCommandRegistry(): VoiceCommandDefinition[] {
  const navParams: VoiceCommandParameter[] = [
    {
      name: "view",
      type: "string",
      required: true,
      description: "Nome della vista",
    },
  ];

  return [
    {
      id: "nav.open",
      domain: "navigation",
      label: "Apri vista",
      description: "Naviga verso una sezione dell'app",
      examples: [
        "apri calendario",
        "vai alle uscite",
        "apri dashboard",
        "mostra mappe",
        "apri meteo",
        "vai al metabolismo",
      ],
      triggerWords: ["apri", "vai a", "mostra", "visualizza", "naviga a"],
      parameters: navParams,
      execute: async (params) => {
        const view = String(requireParam(params, "view")).toLowerCase();
        const viewRoutes: Record<string, string> = {
          calendario: "/calendar",
          uscite: "/rides",
          dashboard: "/dashboard",
          mappe: "/map",
          meteo: "/weather",
          profilo: "/athlete",
          avatar: "/avatar",
          coach: "/coach",
          conoscenza: "/knowledge",
          bm2: "/bm2",
          granfondo: "/granfondo",
          itinerary: "/itinerary",
          pois: "/pois",
          aethermap: "/aethermap",
          confronto: "/comparison",
          heatmap: "/heatmap",
          badge: "/badges",
          zone: "/zones",
          metabolismo: "/metabolism",
          prestazioni: "/performance",
          tracciamento: "/track",
          importa: "/import",
          connessioni: "/settings/connections",
          impostazioni: "/settings",
        };
        const path = viewRoutes[view];
        if (!path) {
          return buildResult(false, `Vista non riconosciuta: ${view}`);
        }
        router.push(path);
        return buildResult(true, `Aperto ${view}`);
      },
    },
    {
      id: "athlete.update_weight",
      domain: "athlete",
      label: "Aggiorna peso",
      description: "Modifica il peso dell'atleta",
      examples: ["modifica peso 78 kg", "aggiorna peso 70 chili", "peso 72 kg"],
      triggerWords: [
        "modifica peso",
        "aggiorna peso",
        "cambia peso",
        "imposta peso",
        "peso",
      ],
      parameters: [
        {
          name: "weight_kg",
          type: "number",
          required: true,
          description: "Peso in kg",
        },
      ],
      execute: async (params) => {
        const weight = Number(requireParam(params, "weight_kg"));
        const store = useAthleteStore();
        await store.updateProfile({ weight_kg: weight });
        return buildResult(true, `Peso aggiornato a ${weight} kg`);
      },
    },
    {
      id: "athlete.update_height",
      domain: "athlete",
      label: "Aggiorna altezza",
      description: "Modifica l'altezza dell'atleta",
      examples: ["modifica altezza 175 cm", "aggiorna altezza 180"],
      triggerWords: [
        "modifica altezza",
        "aggiorna altezza",
        "cambia altezza",
        "imposta altezza",
        "altezza",
      ],
      parameters: [
        {
          name: "height_cm",
          type: "number",
          required: true,
          description: "Altezza in cm",
        },
      ],
      execute: async (params) => {
        const height = Number(requireParam(params, "height_cm"));
        const store = useAthleteStore();
        await store.updateProfile({ height_cm: height });
        return buildResult(true, `Altezza aggiornata a ${height} cm`);
      },
    },
    {
      id: "athlete.update_ftp",
      domain: "athlete",
      label: "Aggiorna FTP",
      description: "Modifica la FTP dell'atleta",
      examples: ["modifica ftp 250 watt", "ftp 280", "aggiorna ftp 270"],
      triggerWords: [
        "modifica ftp",
        "aggiorna ftp",
        "cambia ftp",
        "imposta ftp",
        "ftp",
      ],
      parameters: [
        {
          name: "ftp_watts",
          type: "number",
          required: true,
          description: "FTP in watt",
        },
      ],
      execute: async (params) => {
        const ftp = Number(requireParam(params, "ftp_watts"));
        const store = useAthleteStore();
        await store.updateProfile({ ftp_watts: ftp, ftp });
        return buildResult(true, `FTP aggiornata a ${ftp} watt`);
      },
    },
    {
      id: "athlete.update_max_hr",
      domain: "athlete",
      label: "Aggiorna FC max",
      description: "Modifica la frequenza cardiaca massima",
      examples: [
        "modifica frequenza cardiaca massima 180",
        "fc max 175",
        "aggiorna battito massimo 185",
      ],
      triggerWords: [
        "modifica fc max",
        "aggiorna fc max",
        "cambia fc max",
        "imposta fc max",
        "frequenza cardiaca massima",
        "battito massimo",
      ],
      parameters: [
        {
          name: "max_hr",
          type: "number",
          required: true,
          description: "FC max in bpm",
        },
      ],
      execute: async (params) => {
        const maxHr = Number(requireParam(params, "max_hr"));
        const store = useAthleteStore();
        await store.updateProfile({ max_hr: maxHr });
        return buildResult(true, `FC max aggiornata a ${maxHr} bpm`);
      },
    },
    {
      id: "calendar.add_event",
      domain: "calendar",
      label: "Aggiungi evento calendario",
      description: "Crea un nuovo evento nel calendario",
      examples: [
        "calendario aggiungi ride martedi 24 ottobre alle 21",
        "aggiungi gara domenica 5 maggio",
        "calendario aggiungi recupero domani",
        "calendario aggiungi test giovedi alle 18",
      ],
      triggerWords: [
        "calendario aggiungi",
        "aggiungi al calendario",
        "nuovo evento",
        "crea evento",
        "calendario",
      ],
      parameters: [
        {
          name: "title",
          type: "string",
          required: true,
          description: "Titolo evento",
        },
        {
          name: "date",
          type: "date",
          required: false,
          description: "Data evento (oggi, domani, o data specifica)",
        },
        {
          name: "time",
          type: "time",
          required: false,
          description: "Orario evento",
        },
        {
          name: "event_type",
          type: "event_type",
          required: false,
          description: "Tipo evento",
        },
      ],
      execute: async (params) => {
        const raw = (params._raw as string) || "";
        const date = (params.date as string) || parseItalianDate(raw);
        const time = (params.time as string) || parseTime(raw);
        const eventType =
          (params.event_type as CalendarEvent["event_type"]) ||
          parseEventType(raw) ||
          "training";

        if (!date) {
          return buildResult(
            false,
            "Data non riconosciuta. Specifica un giorno o 'oggi'/'domani'.",
          );
        }

        const dateTime = time ? `${date}T${time}:00` : `${date}T08:00:00`;
        const title = String(params.title || "Nuovo evento").trim();
        const token = localStorage.getItem("bikemaster_token") || "";

        const meResp = await fetch("/api/v1/athletes/me", {
          headers: { Authorization: `Bearer ${token}` },
        });
        if (!meResp.ok) {
          return buildResult(false, "Impossibile ottenere profilo atleta");
        }
        const meData = await meResp.json();
        const athleteId = meData.athlete?.id;
        if (!athleteId) {
          return buildResult(false, "Profilo atleta non trovato");
        }

        const res = await fetch("/api/v1/calendar/events", {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            Authorization: `Bearer ${token}`,
          },
          body: JSON.stringify({
            athlete_id: athleteId,
            date: dateTime,
            title,
            event_type: eventType,
          }),
        });

        if (!res.ok) {
          const err = await res.text();
          return buildResult(false, `Errore creazione evento: ${err}`);
        }

        const ev = await res.json();
        return buildResult(true, `Evento "${title}" creato per il ${date}`, ev);
      },
    },
    {
      id: "rides.add",
      domain: "rides",
      label: "Aggiungi uscita",
      description: "Registra una nuova uscita",
      examples: [
        "aggiungi uscita 80 km 3 ore",
        "nuova uscita 100 km",
        "registra uscita 50 km",
      ],
      triggerWords: [
        "aggiungi uscita",
        "nuova uscita",
        "registra uscita",
        "crea uscita",
        "log uscita",
      ],
      parameters: [
        {
          name: "distance_km",
          type: "number",
          required: false,
          description: "Distanza in km",
        },
        {
          name: "duration_minutes",
          type: "number",
          required: false,
          description: "Durata in minuti",
        },
        {
          name: "name",
          type: "string",
          required: false,
          description: "Nome uscita",
        },
      ],
      execute: async (params) => {
        const _raw = (params._raw as string) || "";
        const distanceKm = params.distance_km
          ? Number(params.distance_km)
          : null;
        const durationMin = params.duration_minutes
          ? Number(params.duration_minutes)
          : null;

        if (!distanceKm && !durationMin) {
          return buildResult(false, "Specifica almeno distanza o durata.");
        }

        const store = useRidesStore();
        const rideData: Record<string, unknown> = {
          name: String(params.name || "Uscita vocale"),
          date: new Date().toISOString(),
          distance_km: distanceKm || 0,
          duration_minutes: durationMin || 0,
          distance_meters: (distanceKm || 0) * 1000,
          duration_seconds: (durationMin || 0) * 60,
          avg_speed_kmh:
            distanceKm && durationMin
              ? distanceKm / (durationMin / 60)
              : undefined,
        };

        const ride = await store.addRide(rideData);
        return buildResult(
          true,
          `Uscita "${ride.name}" registrata: ${distanceKm || 0}km`,
          ride,
        );
      },
    },
    {
      id: "nutrition.log_meal",
      domain: "nutrition",
      label: "Registra pasto",
      description: "Aggiunge un pasto al diario alimentare",
      examples: [
        "stasera cena pasta al ragu",
        "alimentazione cena pasta al ragu 200 grammi",
        "colazione cappuccino cornetto",
        "pranzo risotto 300 grammi",
        "cena insalata 200 grammi",
      ],
      triggerWords: [
        "alimentazione",
        "log pasto",
        "registra pasto",
        "aggiungi pasto",
        "aggiungi alimento",
        "colazione",
        "pranzo",
        "cena",
        "spuntino",
      ],
      parameters: [
        {
          name: "meal_type",
          type: "meal_type",
          required: false,
          description: "Tipo pasto",
        },
        {
          name: "description",
          type: "string",
          required: true,
          description: "Descrizione pasto",
        },
        {
          name: "kcal",
          type: "number",
          required: false,
          description: "Calorie stimate",
        },
      ],
      execute: async (params) => {
        const raw = (params._raw as string) || "";
        const mealType =
          (params.meal_type as FoodLog["meal_type"]) ||
          parseMealType(raw) ||
          "other";
        const description = String(params.description || raw).trim();
        const kcal = params.kcal
          ? Number(params.kcal)
          : estimateKcal(description);

        const today =
          parseItalianDate(raw) || new Date().toISOString().split("T")[0];
        const token = localStorage.getItem("bikemaster_token") || "";

        const meResp = await fetch("/api/v1/athletes/me", {
          headers: { Authorization: `Bearer ${token}` },
        });
        if (!meResp.ok) {
          return buildResult(false, "Impossibile ottenere profilo atleta");
        }
        const meData = await meResp.json();
        const athleteId = meData.athlete?.id;
        if (!athleteId) {
          return buildResult(false, "Profilo atleta non trovato");
        }

        const store = useMetabolismStore();
        const log = await store.createFoodLog({
          date: today,
          meal_type: mealType,
          description,
          kcal,
        });

        const calResp = await fetch("/api/v1/calendar/events", {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            Authorization: `Bearer ${token}`,
          },
          body: JSON.stringify({
            athlete_id: athleteId,
            date: today,
            title: `${getMealLabel(mealType)}: ${description}`,
            event_type: "other",
            description: `Pasto registrato: ${description} (${kcal} kcal)`,
          }),
        });
        if (!calResp.ok) {
          const err = await calResp.text().catch(() => "");
          console.warn("Errore creazione evento calendario pasto:", err);
        }

        const recalcResp = await fetch(
          `/api/v1/metabolism/recalculate?date=${today}`,
          {
            method: "POST",
            headers: { Authorization: `Bearer ${token}` },
          },
        );
        let summaryMsg = "";
        if (recalcResp.ok) {
          const summary = await recalcResp.json();
          summaryMsg = ` Intake: ${Math.round(summary.intake_kcal || 0)} kcal, Balance: ${Math.round(summary.balance_kcal || 0)} kcal`;
        }

        return buildResult(
          true,
          `Pasto "${description}" registrato (${kcal} kcal).${summaryMsg}`,
          log,
        );
      },
    },
    {
      id: "tracking.start",
      domain: "tracking",
      label: "Avvia tracciamento",
      description: "Inizia il tracciamento GPS di una uscita",
      examples: [
        "inizia tracciamento",
        "avvia uscita",
        "start tracking",
        "parti con tracciamento",
      ],
      triggerWords: [
        "inizia tracciamento",
        "avvia tracciamento",
        "start tracking",
        "parti",
        "avvia uscita",
      ],
      parameters: [],
      execute: async () => {
        router.push("/track");
        return buildResult(true, "Tracciamento avviato");
      },
    },
    {
      id: "tracking.stop",
      domain: "tracking",
      label: "Ferma tracciamento",
      description: "Ferma il tracciamento GPS corrente",
      examples: [
        "ferma tracciamento",
        "termina uscita",
        "stop tracking",
        "salva uscita",
      ],
      triggerWords: [
        "ferma tracciamento",
        "termina uscita",
        "stop tracking",
        "salva uscita",
        "fine uscita",
      ],
      parameters: [],
      execute: async () => {
        if (window.BikeTracking?.stopTracking) {
          window.BikeTracking.stopTracking();
        }
        return buildResult(true, "Tracciamento fermato");
      },
    },
    {
      id: "settings.toggle_theme",
      domain: "settings",
      label: "Cambia tema",
      description: "Alterna tema scuro e chiaro",
      examples: [
        "cambia tema",
        "tema scuro",
        "tema chiaro",
        "modalita scura",
        "modalita chiara",
      ],
      triggerWords: [
        "cambia tema",
        "tema scuro",
        "tema chiaro",
        "modalita scura",
        "modalita chiara",
        "attiva tema chiaro",
        "attiva tema scuro",
      ],
      parameters: [
        {
          name: "dark",
          type: "boolean",
          required: false,
          description: "Tema scuro (true) o chiaro (false)",
        },
      ],
      execute: async (params) => {
        const ui = useUIStore();
        const dark =
          params.dark !== undefined ? Boolean(params.dark) : !ui.isDark;
        if (dark !== ui.isDark) {
          ui.toggleTheme();
        }
        return buildResult(
          true,
          dark ? "Tema scuro attivo" : "Tema chiaro attivo",
        );
      },
    },
    {
      id: "settings.toggle_sidebar",
      domain: "settings",
      label: "Mostra/nascondi sidebar",
      description: "Alterna visibilita sidebar",
      examples: [
        "mostra sidebar",
        "nascondi sidebar",
        "apri menu",
        "chiudi menu",
        "toggle sidebar",
      ],
      triggerWords: [
        "mostra sidebar",
        "nascondi sidebar",
        "apri menu",
        "chiudi menu",
        "toggle sidebar",
      ],
      parameters: [],
      execute: async () => {
        const ui = useUIStore();
        ui.toggleSidebar();
        return buildResult(
          true,
          ui.sidebarCollapsed ? "Sidebar nascosta" : "Sidebar visibile",
        );
      },
    },
    {
      id: "metabolism.show_calories",
      domain: "nutrition",
      label: "Mostra calorie",
      description: "Visualizza il riepilogo calorie/metabolismo",
      examples: ["leggi calorie", "mostra calorie", "quante calorie"],
      triggerWords: [
        "leggi calorie",
        "mostra calorie",
        "calorie",
        "riepilogo calorie",
      ],
      parameters: [],
      execute: async () => {
        router.push("/metabolism");
        return buildResult(true, "Apro metabolismo");
      },
    },
    {
      id: "rides.export_csv",
      domain: "rides",
      label: "Esporta uscite",
      description: "Esporta le uscite in CSV",
      examples: ["esporta uscite", "esporta csv", "scarica uscite"],
      triggerWords: [
        "esporta uscite",
        "esporta csv",
        "scarica uscite",
        "esporta",
      ],
      parameters: [],
      execute: async () => {
        const store = useRidesStore();
        const headers = [
          "Date",
          "Distance (km)",
          "Duration (min)",
          "Avg Speed (km/h)",
          "Elevation (m)",
          "Calories",
        ];
        const rows = store.rides.map((r) => [
          r.date,
          r.distance_km,
          r.duration_minutes,
          r.avg_speed_kmh ?? "",
          r.elevation_gain_m ?? "",
          r.calories ?? "",
        ]);
        const csv = [
          headers.join(","),
          ...rows.map((row) => row.join(",")),
        ].join("\n");
        const blob = new Blob(["\uFEFF" + csv], {
          type: "text/csv;charset=utf-8;",
        });
        const url = URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.href = url;
        a.download = `rides_export_${new Date().toISOString().slice(0, 10)}.csv`;
        a.click();
        URL.revokeObjectURL(url);
        return buildResult(true, "CSV esportato");
      },
    },
    {
      id: "rides.clear_filters",
      domain: "rides",
      label: "Resetta filtri uscite",
      description: "Resetta i filtri e ricarica tutte le uscite",
      examples: [
        "resetta filtri uscite",
        "cancella filtri uscite",
        "mostra tutte le uscite",
      ],
      triggerWords: [
        "resetta filtri uscite",
        "cancella filtri uscite",
        "mostra tutte le uscite",
        "reset uscite",
      ],
      parameters: [],
      execute: async () => {
        const store = useRidesStore();
        store.clearFilters();
        await store.fetchRides();
        return buildResult(true, "Filtri resettati");
      },
    },
    {
      id: "import.connect_strava",
      domain: "connections",
      label: "Connetti Strava",
      description: "Avvia connessione Strava",
      examples: ["connetti strava", "collega strava"],
      triggerWords: ["connetti strava", "collega strava", "strava connetti"],
      parameters: [],
      execute: async () => {
        router.push("/settings/connections");
        return buildResult(true, "Apro connessioni per Strava");
      },
    },
    {
      id: "import.sync_strava",
      domain: "connections",
      label: "Sincronizza Strava",
      description: "Sincronizza le uscite da Strava",
      examples: ["sincronizza strava", "sync strava"],
      triggerWords: [
        "sincronizza strava",
        "sync strava",
        "strava sync",
        "importa da strava",
      ],
      parameters: [],
      execute: async () => {
        const token = localStorage.getItem("bikemaster_token") || "";
        const resp = await fetch(
          "/api/v1/import/strava/sync?background=false",
          {
            method: "POST",
            headers: token ? { Authorization: `Bearer ${token}` } : {},
          },
        );
        if (!resp.ok) {
          const err = await resp.json().catch(() => ({}));
          return buildResult(false, err.detail || "Sync Strava fallita");
        }
        const result = await resp.json();
        return buildResult(
          true,
          `Importati ${result.imported} uscite da Strava`,
        );
      },
    },
    {
      id: "import.connect_google_fit",
      domain: "connections",
      label: "Connetti Google Fit",
      description: "Avvia connessione Google Fit",
      examples: ["connetti google fit", "collega google fit"],
      triggerWords: [
        "connetti google fit",
        "collega google fit",
        "google fit connetti",
      ],
      parameters: [],
      execute: async () => {
        router.push("/settings/connections");
        return buildResult(true, "Apro connessioni per Google Fit");
      },
    },
    {
      id: "import.upload_gpx",
      domain: "import",
      label: "Carica file GPX",
      description: "Apri pannello import per caricare file",
      examples: ["carica file", "carica gpx", "importa file"],
      triggerWords: [
        "carica file",
        "carica gpx",
        "importa file",
        "carica tracciamento",
      ],
      parameters: [],
      execute: async () => {
        router.push("/import");
        return buildResult(true, "Apro import");
      },
    },
    {
      id: "heatmap.load",
      domain: "maps",
      label: "Carica heatmap",
      description: "Carica la vista heatmap",
      examples: ["carica heatmap", "mostra heatmap"],
      triggerWords: ["carica heatmap", "mostra heatmap", "heatmap"],
      parameters: [],
      execute: async () => {
        router.push("/heatmap");
        return buildResult(true, "Apro heatmap");
      },
    },
    {
      id: "badges.load",
      domain: "badges",
      label: "Carica badge",
      description: "Carica i badge dell'atleta",
      examples: ["carica badge", "mostra badge"],
      triggerWords: ["carica badge", "mostra badge", "badge"],
      parameters: [],
      execute: async () => {
        router.push("/badges");
        return buildResult(true, "Apro badge");
      },
    },
    {
      id: "weather.load",
      domain: "weather",
      label: "Mostra meteo",
      description: "Mostra il meteo per l'uscita",
      examples: ["mostra meteo", "apri meteo", "meteo"],
      triggerWords: ["mostra meteo", "apri meteo", "meteo", "che tempo fa"],
      parameters: [],
      execute: async () => {
        router.push("/weather");
        return buildResult(true, "Apro meteo");
      },
    },
    {
      id: "knowledge.search",
      domain: "knowledge",
      label: "Cerca conoscenza",
      description: "Cerca nella knowledge base",
      examples: [
        "cerca conoscenza FTP",
        "cosa e la soglia",
        "ricerca allenamento",
      ],
      triggerWords: [
        "cerca conoscenza",
        "cerca nel knowledge",
        "cerca informazione",
        "ricerca",
      ],
      parameters: [
        {
          name: "query",
          type: "string",
          required: true,
          description: "Query di ricerca",
        },
      ],
      execute: async (params) => {
        const query = String(requireParam(params, "query"));
        router.push({ path: "/knowledge", query: { q: query } });
        return buildResult(true, `Ricerca: ${query}`);
      },
    },
    {
      id: "bm2.simulate",
      domain: "bm2",
      label: "Simula gara",
      description: "Avvia simulazione gara BM2",
      examples: ["simula gara", "simula uscita"],
      triggerWords: ["simula gara", "simula uscita", "avvia simulazione"],
      parameters: [],
      execute: async () => {
        router.push("/bm2");
        return buildResult(true, "Apro BM2");
      },
    },
    {
      id: "bm2.validate",
      domain: "bm2",
      label: "Valida piano",
      description: "Valida il piano di allenamento",
      examples: ["valida piano", "valida allenamento"],
      triggerWords: ["valida piano", "valida allenamento", "valida workout"],
      parameters: [],
      execute: async () => {
        router.push("/bm2");
        return buildResult(true, "Apro BM2");
      },
    },
    {
      id: "granfondo.generate",
      domain: "granfondo",
      label: "Genera piano granfondo",
      description: "Genera un piano granfondo",
      examples: ["genera piano granfondo", "crea piano granfondo"],
      triggerWords: [
        "genera piano granfondo",
        "crea piano granfondo",
        "piano granfondo",
      ],
      parameters: [],
      execute: async () => {
        router.push("/granfondo");
        return buildResult(true, "Apro granfondo");
      },
    },
    {
      id: "tracking.pause",
      domain: "tracking",
      label: "Pausa tracciamento",
      description: "Metti in pausa il tracciamento",
      examples: ["pausa tracciamento", "pausa uscita", "metti in pausa"],
      triggerWords: [
        "pausa tracciamento",
        "pausa uscita",
        "metti in pausa",
        "pausa",
      ],
      parameters: [],
      execute: async () => {
        if (window.BikeTracking?.pauseTracking) {
          window.BikeTracking.pauseTracking();
        }
        return buildResult(true, "Tracciamento in pausa");
      },
    },
    {
      id: "tracking.resume",
      domain: "tracking",
      label: "Riprendi tracciamento",
      description: "Riprende il tracciamento in pausa",
      examples: [
        "riprendi tracciamento",
        "riprendi uscita",
        "continua tracciamento",
      ],
      triggerWords: [
        "riprendi tracciamento",
        "riprendi uscita",
        "continua tracciamento",
        "riprendi",
      ],
      parameters: [],
      execute: async () => {
        if (window.BikeTracking?.resumeTracking) {
          window.BikeTracking.resumeTracking();
        }
        return buildResult(true, "Tracciamento ripreso");
      },
    },
    {
      id: "calendar.go_today",
      domain: "calendar",
      label: "Vai a oggi",
      description: "Mostra il giorno odierno nel calendario",
      examples: ["vai a oggi calendario", "mostra oggi"],
      triggerWords: ["vai a oggi calendario", "mostra oggi", "calendario oggi"],
      parameters: [],
      execute: async () => {
        router.push("/calendar");
        return buildResult(true, "Apro calendario");
      },
    },
    {
      id: "sync.set_local",
      domain: "sync",
      label: "Sync locale",
      description: "Imposta modalita sincronizzazione locale",
      examples: ["sync locale", "modalita locale"],
      triggerWords: [
        "sync locale",
        "modalita locale",
        "sincronizzazione locale",
        "imposta sync locale",
      ],
      parameters: [],
      execute: async () => {
        const token = localStorage.getItem("bikemaster_token") || "";
        const resp = await fetch("/api/v1/sync/settings", {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            ...(token ? { Authorization: `Bearer ${token}` } : {}),
          },
          body: JSON.stringify({ mode: "local" }),
        });
        if (!resp.ok) return buildResult(false, "Impostazione sync fallita");
        return buildResult(true, "Modalita sincronizzazione locale attiva");
      },
    },
    {
      id: "sync.set_cloud",
      domain: "sync",
      label: "Sync cloud",
      description: "Imposta modalita sincronizzazione cloud",
      examples: ["sync cloud", "modalita cloud"],
      triggerWords: [
        "sync cloud",
        "modalita cloud",
        "sincronizzazione cloud",
        "imposta sync cloud",
      ],
      parameters: [],
      execute: async () => {
        const token = localStorage.getItem("bikemaster_token") || "";
        const resp = await fetch("/api/v1/sync/settings", {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            ...(token ? { Authorization: `Bearer ${token}` } : {}),
          },
          body: JSON.stringify({ mode: "cloud" }),
        });
        if (!resp.ok) return buildResult(false, "Impostazione sync fallita");
        return buildResult(true, "Modalita sincronizzazione cloud attiva");
      },
    },
    {
      id: "sync.refresh",
      domain: "sync",
      label: "Aggiorna sync",
      description: "Legge lo stato di sincronizzazione",
      examples: ["aggiorna sync", "stato sincronizzazione"],
      triggerWords: ["aggiorna sync", "stato sincronizzazione", "sync status"],
      parameters: [],
      execute: async () => {
        const token = localStorage.getItem("bikemaster_token") || "";
        const resp = await fetch("/api/v1/sync/status", {
          headers: token ? { Authorization: `Bearer ${token}` } : {},
        });
        if (!resp.ok) return buildResult(false, "Stato sync non disponibile");
        const data = await resp.json();
        return buildResult(
          true,
          `Sync: ${data.mode}, in attesa: ${data.pending_count ?? 0}`,
        );
      },
    },
    {
      id: "sync.export",
      domain: "sync",
      label: "Esporta dati",
      description: "Esporta i dati dell'app",
      examples: ["esporta dati", "backup dati"],
      triggerWords: ["esporta dati", "backup dati", "esporta"],
      parameters: [],
      execute: async () => {
        const token = localStorage.getItem("bikemaster_token") || "";
        const resp = await fetch("/api/v1/sync/export", {
          headers: token ? { Authorization: `Bearer ${token}` } : {},
        });
        if (!resp.ok) return buildResult(false, "Esportazione fallita");
        const blob = await resp.blob();
        const url = URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.href = url;
        a.download = `bikemaster_export_${new Date().toISOString().slice(0, 10)}.json`;
        a.click();
        URL.revokeObjectURL(url);
        return buildResult(true, "Dati esportati");
      },
    },
    {
      id: "sync.import_data",
      domain: "sync",
      label: "Importa dati",
      description: "Importa dati nell'app",
      examples: ["importa dati", "ripristina dati"],
      triggerWords: ["importa dati", "ripristina dati", "importa"],
      parameters: [],
      execute: async () => {
        const token = localStorage.getItem("bikemaster_token") || "";
        const resp = await fetch("/api/v1/sync/import", {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            ...(token ? { Authorization: `Bearer ${token}` } : {}),
          },
          body: JSON.stringify({ rides: [] }),
        });
        if (!resp.ok) {
          const err = await resp.json().catch(() => ({}));
          return buildResult(false, err.detail || "Importazione fallita");
        }
        return buildResult(true, "Dati importati");
      },
    },
    {
      id: "rides.analyze",
      domain: "rides",
      label: "Analizza uscita",
      description: "Analizza l'ultima uscita o una specifica",
      examples: ["analizza uscita", "analizza ultima uscita"],
      triggerWords: ["analizza uscita", "analizza ultima uscita", "analizza"],
      parameters: [
        {
          name: "ride_id",
          type: "number",
          required: false,
          description: "ID uscita",
        },
      ],
      execute: async (params) => {
        const store = useRidesStore();
        const rideId = params.ride_id
          ? Number(params.ride_id)
          : store.rides[0]?.id;
        if (!rideId) return buildResult(false, "Nessuna uscita da analizzare");
        router.push({ path: "/rides", query: { analyze: String(rideId) } });
        return buildResult(true, `Analisi uscita ${rideId}`);
      },
    },
    {
      id: "weather.load",
      domain: "weather",
      label: "Mostra meteo",
      description: "Mostra il meteo per l'uscita",
      examples: ["mostra meteo", "apri meteo", "meteo"],
      triggerWords: ["mostra meteo", "apri meteo", "meteo", "che tempo fa"],
      parameters: [],
      execute: async () => {
        router.push("/weather");
        return buildResult(true, "Apro meteo");
      },
    },
    {
      id: "heatmap.load",
      domain: "maps",
      label: "Carica heatmap",
      description: "Carica la vista heatmap",
      examples: ["carica heatmap", "mostra heatmap"],
      triggerWords: ["carica heatmap", "mostra heatmap", "heatmap"],
      parameters: [],
      execute: async () => {
        router.push("/heatmap");
        return buildResult(true, "Apro heatmap");
      },
    },
    {
      id: "badges.load",
      domain: "badges",
      label: "Carica badge",
      description: "Carica i badge dell'atleta",
      examples: ["carica badge", "mostra badge"],
      triggerWords: ["carica badge", "mostra badge", "badge"],
      parameters: [],
      execute: async () => {
        router.push("/badges");
        return buildResult(true, "Apro badge");
      },
    },
    {
      id: "itinerary.load",
      domain: "itinerary",
      label: "Mostra itinerari",
      description: "Carica la vista itinerari",
      examples: ["mostra itinerari", "apri itinerari"],
      triggerWords: ["mostra itinerari", "apri itinerari", "itinerari"],
      parameters: [],
      execute: async () => {
        router.push("/itinerary");
        return buildResult(true, "Apro itinerari");
      },
    },
  ];
}

export function parseTranscript(
  transcript: string,
  commands: VoiceCommandDefinition[],
): ParsedCommand | null {
  const lower = transcript.toLowerCase().trim();
  let bestMatch: {
    def: VoiceCommandDefinition;
    score: number;
    params: Record<string, unknown>;
  } | null = null;

  for (const cmd of commands) {
    const matchedTrigger = cmd.triggerWords.find((tw) =>
      lower.includes(tw.toLowerCase()),
    );
    if (!matchedTrigger) continue;

    const params: Record<string, unknown> = { _raw: transcript };

    for (const p of cmd.parameters) {
      if (p.type === "number") {
        const n = parseNumber(lower);
        if (n !== null) {
          params[p.name] = n;
        }
      } else if (p.type === "date") {
        const d = parseItalianDate(lower);
        if (d) params[p.name] = d;
      } else if (p.type === "time") {
        const t = parseTime(lower);
        if (t) params[p.name] = t;
      } else if (p.type === "boolean") {
        const hasScuro = lower.includes("scuro") || lower.includes("dark");
        const hasChiaro = lower.includes("chiaro") || lower.includes("light");
        if (hasScuro) params[p.name] = true;
        else if (hasChiaro) params[p.name] = false;
      } else if (p.type === "meal_type") {
        const mt = parseMealType(lower);
        if (mt) params[p.name] = mt;
      } else if (p.type === "event_type") {
        const et = parseEventType(lower);
        if (et) params[p.name] = et;
      } else if (p.type === "string" && p.name === "description") {
        const desc = lower
          .replace(matchedTrigger.toLowerCase(), "")
          .trim()
          .replace(/^\d+\s*/, "")
          .trim();
        if (desc) params[p.name] = desc;
      } else if (p.type === "string" && p.name === "view") {
        const viewPart = lower
          .replace(matchedTrigger.toLowerCase(), "")
          .trim()
          .toLowerCase();
        if (viewPart) params[p.name] = viewPart;
      }
    }

    const requiredMissing = cmd.parameters
      .filter((p) => p.required)
      .some((p) => params[p.name] === undefined);

    if (requiredMissing) continue;

    const triggerLen = matchedTrigger.length;
    const score =
      triggerLen + (transcript.length - matchedTrigger.length) * 0.01;

    if (!bestMatch || score > bestMatch.score) {
      bestMatch = { def: cmd, score, params };
    }
  }

  if (!bestMatch) return null;

  return {
    definition: bestMatch.def,
    params: bestMatch.params,
    rawTranscript: transcript,
    confidence: Math.min(bestMatch.score / transcript.length, 1),
  };
}

let logIdCounter = 0;
export function createLogEntry(
  transcript: string,
  parsed: ParsedCommand | null,
  result: VoiceCommandResult,
): VoiceCommandLogEntry {
  return {
    id: `vc_${Date.now()}_${++logIdCounter}`,
    timestamp: new Date(),
    transcript,
    commandId: parsed?.definition.id || null,
    success: result.success,
    message: result.message,
    params: parsed?.params || {},
  };
}
