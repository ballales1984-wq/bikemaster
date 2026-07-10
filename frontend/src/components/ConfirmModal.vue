<template>
  <Teleport to="body">
    <transition name="fade">
      <div v-if="visible" class="modal-overlay" @click.self="cancel">
        <div
          ref="dialogRef"
          class="modal-dialog"
          role="dialog"
          aria-modal="true"
          :aria-labelledby="titleId"
          :aria-describedby="messageId"
        >
          <h3 :id="titleId">
            {{ title }}
          </h3>
          <p :id="messageId">
            {{ message }}
          </p>
          <div class="modal-actions">
            <button class="btn btn-secondary" @click="cancel">
              {{ cancelLabel }}
            </button>
            <button class="btn btn-danger" @click="confirm">
              {{ confirmLabel }}
            </button>
          </div>
        </div>
      </div>
    </transition>
  </Teleport>
</template>

<script setup lang="ts">
import { nextTick, onBeforeUnmount, ref, watch } from "vue";

const props = defineProps({
  modelValue: { type: Boolean, default: false },
  title: { type: String, default: "Confirm" },
  message: { type: String, default: "Are you sure?" },
  confirmLabel: { type: String, default: "Confirm" },
  cancelLabel: { type: String, default: "Cancel" },
});

const emit = defineEmits(["update:modelValue", "confirm", "cancel"]);

const visible = ref(false);
const dialogRef = ref<HTMLElement | null>(null);
const uid = Math.random().toString(36).slice(2);
const titleId = `confirm-title-${uid}`;
const messageId = `confirm-message-${uid}`;

function onKeydown(e: KeyboardEvent) {
  if (e.key === "Escape") {
    e.preventDefault();
    cancel();
    return;
  }
  if (e.key === "Tab" && dialogRef.value) {
    const focusables = dialogRef.value.querySelectorAll<HTMLElement>(
      'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])',
    );
    if (!focusables.length) return;
    const first = focusables[0];
    const last = focusables[focusables.length - 1];
    if (e.shiftKey && document.activeElement === first) {
      e.preventDefault();
      last.focus();
    } else if (!e.shiftKey && document.activeElement === last) {
      e.preventDefault();
      first.focus();
    }
  }
}

function open() {
  document.addEventListener("keydown", onKeydown);
  document.body.style.overflow = "hidden";
  nextTick(() => {
    dialogRef.value?.querySelector("button")?.focus();
  });
}

function close() {
  document.removeEventListener("keydown", onKeydown);
  document.body.style.overflow = "";
}

watch(
  () => props.modelValue,
  (v) => {
    visible.value = v;
    if (v) open();
    else close();
  },
  { immediate: true },
);

onBeforeUnmount(close);

function confirm() {
  emit("update:modelValue", false);
  emit("confirm");
}

function cancel() {
  emit("update:modelValue", false);
  emit("cancel");
}
</script>
