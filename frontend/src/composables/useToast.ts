/**
 * Composable per le notifiche toast.
 * Gestisce una lista reattiva di toast con tipologia (success/error/warning/
 * info), auto-rimozione con animazione e pulizia dei timer allo smontaggio.
 * Espone `items`, `add`, `show`, `remove` e gli helper `success`/`error`/
 * `warning`/`info`.
 */
import { onBeforeUnmount, ref } from "vue";

interface ToastItem {
  id: number;
  message: string;
  type: "success" | "error" | "warning" | "info";
  exiting: boolean;
}

let nextId = 1;

function useToast() {
  const items = ref<ToastItem[]>([]);
  const timers = new Set<ReturnType<typeof setTimeout>>();

  function schedule(fn: () => void, ms: number) {
    const id = setTimeout(() => {
      timers.delete(id);
      fn();
    }, ms);
    timers.add(id);
  }

  function add(
    message: string,
    type: "success" | "error" | "warning" | "info" = "info",
    ms: number = 3000,
  ) {
    const id = nextId++;
    items.value.push({ id, message, type, exiting: false });
    schedule(() => removeWithAnimation(id), ms);
  }

  function remove(id: number) {
    items.value = items.value.filter((t) => t.id !== id);
  }

  function removeWithAnimation(id: number) {
    const toast = items.value.find((t) => t.id === id);
    if (toast) {
      toast.exiting = true;
      schedule(() => remove(id), 300);
    }
  }

  function success(message: string, ms?: number) {
    add(message, "success", ms);
  }
  function error(message: string, ms?: number) {
    add(message, "error", ms);
  }
  function warning(message: string, ms?: number) {
    add(message, "warning", ms);
  }
  function info(message: string, ms?: number) {
    add(message, "info", ms);
  }
  function show(message: string, type?: string, ms?: number) {
    add(
      message,
      (type as "success" | "error" | "warning" | "info") || "info",
      ms,
    );
  }

  onBeforeUnmount(() => {
    for (const id of timers) clearTimeout(id);
    timers.clear();
  });

  return {
    items,
    add,
    show,
    remove,
    success,
    error,
    warning,
    info,
  };
}

export { useToast };
