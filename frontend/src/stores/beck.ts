/**
 * Store Beck: assessment Beck Depression Inventory (BDI).
 */
import { defineStore } from "pinia";
import { ref, computed } from "vue";
import type {
  BeckAssessment,
  BeckHistory,
  BeckItemScore,
  BeckItemOption,
} from "../types/index";
import { apiGet, apiPost, ApiError } from "../utils/api";
import { useAuthStore } from "./auth";

const BECK_ITEMS: BeckItemOption[] = [
  ["Non mi sento triste", 0],
  ["Mi sento triste", 1],
  ["Mi sento sempre triste e non riesco a tirarmi su", 2],
  ["Sono triste o infelice e non riesco a provare sollievo", 3],
  ["Non sono scoraggiato per il futuro", 0],
  ["Mi sento più scoraggiato per il futuro rispetto al solito", 1],
  ["Non aspetto niente di buono dal futuro", 2],
  ["Il futuro è senza speranza e non vedo modo di migliorare le cose", 3],
  ["Non mi sento un fallito", 0],
  ["Ho fallito più di quanto avrei dovuto", 1],
  ["Guardo indietro e vedo solo fallimenti", 2],
  ["Come persona mi sento un completo fallito", 3],
  ["Non provo più piacere come prima", 0],
  ["Non provo piacere come una volta", 1],
  ["Non provo più un piacere vero", 2],
  ["Non sono più soddisfatto di niente", 3],
  ["Non mi sento particolarmente in colpa", 0],
  ["Mi sento in colpa per molte cose che ho fatto o che non ho fatto", 1],
  ["Mi sento quasi sempre in colpa", 2],
  ["Mi sento in colpa per tutto", 3],
  ["Non penso che stia peggio degli altri", 0],
  ["Mi critico per i miei errori o le mie debolezze", 1],
  ["Mi biasimo sempre per tutto", 2],
  ["Mi sento colpevole per ogni piccola cosa", 3],
  ["Non ho voglia di suicidarmi", 0],
  ["A volte penso che sarebbe meglio se non fossi vivo", 1],
  ["Vorrei soffermarmi su queste idee", 2],
  ["Non vedo alternative e penso al suicidio", 3],
  ["Non piango più di una volta", 0],
  ["Piango più spesso di prima", 1],
  ["Ora piango sempre, anche per cose piccole", 2],
  ["Prima riuscivo a piangere, ma ora non ci riesco anche se vorrei", 3],
  ["Non sono più irritabile del solito", 0],
  ["Mi infastidisco più facilmente del solito", 1],
  ["Sono irritabile quasi sempre", 2],
  ["Non mi irrito più per le cose che prima mi davano fastidio", 3],
  ["Non ho perso interesse per gli altri", 0],
  ["Ho meno interesse per gli altri rispetto al solito", 1],
  ["Ho perso quasi tutto l'interesse per gli altri", 2],
  ["Non ho più alcun interesse per gli altri", 3],
  ["Prendo decisioni più o meno come prima", 0],
  ["Rimando le decisioni più di una volta", 1],
  ["Ho difficoltà a prendere decisioni", 2],
  ["Non riesco più a prendere nessuna decisione", 3],
  ["Non mi sembra di avere un aspetto peggiore del solito", 0],
  ["Mi preoccupo di avere un aspetto invecchiato o poco attraente", 1],
  ["Sono convinto di avere un aspetto brutto o inguardabile", 2],
  [
    "L'aspetto fisico mi fa stare così male che non riesco a guardarmi allo specchio",
    3,
  ],
  ["Posso lavorare più o meno come prima", 0],
  ["Mi serve uno sforzo in più per iniziare a fare qualcosa", 1],
  ["Devo costringermi a fare qualsiasi cosa", 2],
  ["Non riesco a fare niente per niente", 3],
  ["Non dormo peggio del solito", 0],
  ["Mi sveglio prima del solito e ho difficoltà a riaddormentarmi", 1],
  ["Mi sveglio diverse ore prima e non riesco a riaddormentarmi", 2],
  [
    "Mi sveglio così presto che non riesco più a dormire per il resto della notte",
    3,
  ],
  ["Non sono più stanco del solito", 0],
  ["Mi stanco più facilmente del solito", 1],
  ["Mi stanco per qualsiasi cosa", 2],
  ["Sono troppo stanco per fare anche le cose più semplici", 3],
  ["Il mio appetito non è peggiorato", 0],
  ["Non ho più appetito come una volta", 1],
  ["Il mio appetito è molto peggiorato", 2],
  ["Non ho appetito per niente", 3],
  ["Non ho perso peso di recente", 0],
  ["Ho perso più di 2 kg e mezzo", 1],
  ["Ho perso più di 5 kg", 2],
  ["Ho perso più di 7 kg e mezzo", 3],
  ["Non sono più preoccupato per la mia salute di prima", 0],
  ["Mi preoccupo per problemi fisici come dolori o disturbi", 1],
  ["Sono molto preoccupato per i miei disturbi fisici", 2],
  [
    "Sono così preoccupato per i miei disturbi che non riesco a pensare ad altro",
    3,
  ],
  ["Non ho visto cambiamenti nel mio interesse sessuale", 0],
  ["Ho meno interesse sessuale di prima", 1],
  ["Il mio interesse sessuale è molto diminuito", 2],
  ["Ho perso completamente l'interesse sessuale", 3],
];

export const useBeckStore = defineStore("beck", () => {
  const auth = useAuthStore();
  const items = ref<BeckItemOption[]>(BECK_ITEMS);
  const answers = ref<Map<number, BeckItemScore>>(new Map());
  const currentNotes = ref<string>("");
  const assessments = ref<BeckAssessment[]>([]);
  const latest = ref<BeckAssessment | null>(null);
  const history = ref<BeckHistory | null>(null);
  const loading = ref(false);
  const saving = ref(false);
  const error = ref<string | null>(null);

  const totalScore = computed(() =>
    Array.from(answers.value.values()).reduce(
      (sum, score) => (sum + score) as BeckItemScore,
      0 as BeckItemScore,
    ),
  );
  const severity = computed(() => {
    const score = totalScore.value;
    if (score <= 13) return "minimal";
    if (score <= 19) return "mild";
    if (score <= 28) return "moderate";
    return "severe";
  });
  const progress = computed(() =>
    Math.min(100, (answers.value.size / BECK_ITEMS.length) * 100),
  );
  const isComplete = computed(() => answers.value.size === BECK_ITEMS.length);

  function reset() {
    answers.value = new Map();
    currentNotes.value = "";
    error.value = null;
  }

  async function fetchHistory(): Promise<BeckHistory | null> {
    if (!auth.isLoggedIn) return null;
    loading.value = true;
    error.value = null;
    try {
      const data = await apiGet<BeckHistory>("/api/v1/beck/history");
      history.value = data;
      assessments.value = data.items || [];
      latest.value = data.latest || null;
      return data;
    } catch (e) {
      error.value =
        e instanceof Error ? e.message : "Failed to load Beck history";
      return null;
    } finally {
      loading.value = false;
    }
  }

  async function fetchLatest(): Promise<BeckAssessment | null> {
    if (!auth.isLoggedIn) return null;
    loading.value = true;
    error.value = null;
    try {
      const data = await apiGet<BeckAssessment>(
        "/api/v1/beck/assessments/latest",
      );
      latest.value = data;
      return data;
    } catch (e) {
      if (e instanceof ApiError && e.status === 404) {
        latest.value = null;
        return null;
      }
      error.value =
        e instanceof Error
          ? e.message
          : "Failed to load latest Beck assessment";
      return null;
    } finally {
      loading.value = false;
    }
  }

  async function submit(): Promise<BeckAssessment | null> {
    if (!auth.isLoggedIn) throw new Error("Not authenticated");
    if (!isComplete.value) throw new Error("Assessment is incomplete");
    saving.value = true;
    error.value = null;
    try {
      const answersPayload = Array.from(answers.value.entries()).map(
        ([index, score]) => [index, score],
      );
      const data = await apiPost<BeckAssessment>("/api/v1/beck/assessments", {
        answers: answersPayload,
        notes: currentNotes.value || undefined,
      });
      assessments.value.unshift(data);
      latest.value = data;
      if (history.value) {
        history.value.items.unshift(data);
        history.value.latest = data;
        history.value.trend.unshift({
          date: data.created_at,
          score: data.total_score,
          severity: data.severity,
        });
      }
      reset();
      return data;
    } catch (e) {
      error.value =
        e instanceof Error ? e.message : "Failed to submit Beck assessment";
      throw e;
    } finally {
      saving.value = false;
    }
  }

  function setAnswer(index: number, score: BeckItemScore) {
    answers.value.set(index, score);
  }

  function updateNotes(notes: string) {
    currentNotes.value = notes;
  }

  function clear() {
    assessments.value = [];
    latest.value = null;
    history.value = null;
    error.value = null;
    reset();
  }

  return {
    items,
    answers,
    currentNotes,
    assessments,
    latest,
    history,
    loading,
    saving,
    error,
    totalScore,
    severity,
    progress,
    isComplete,
    reset,
    setAnswer,
    updateNotes,
    fetchHistory,
    fetchLatest,
    submit,
    clear,
  };
});
