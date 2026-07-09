import { ref } from "vue";

interface ToastItem {
  id: number;
  message: string;
  type: "success" | "error" | "warning" | "info";
  exiting: boolean;
}

function useToast() {
  const items = ref<ToastItem[]>([]);
  let nextId = 1;

  function add(
    message: string,
    type: "success" | "error" | "warning" | "info" = "info",
    ms: number = 3000,
  ) {
    const id = nextId++;
    items.value.push({ id, message, type, exiting: false });
    setTimeout(() => removeWithAnimation(id), ms);
  }

  function remove(id: number) {
    items.value = items.value.filter((t) => t.id !== id);
  }

  function removeWithAnimation(id: number) {
    const toast = items.value.find((t) => t.id === id);
    if (toast) {
      toast.exiting = true;
      setTimeout(() => remove(id), 300);
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
    add(message, (type as any) || "info", ms);
  }

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
