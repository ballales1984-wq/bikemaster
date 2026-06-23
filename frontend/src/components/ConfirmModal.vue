<template>
  <Teleport to="body">
    <Transition name="fade">
      <div v-if="visible" class="modal-overlay" @click.self="cancel">
        <div class="modal-dialog" role="dialog" aria-modal="true">
          <h3>{{ title }}</h3>
          <p>{{ message }}</p>
<div class="modal-actions">
         <button class="btn btn-secondary" @click="cancel" @touchstart="cancel">{{ cancelLabel }}</button>
         <button class="btn btn-danger" @click="confirm" @touchstart="confirm">{{ confirmLabel }}</button>
       </div>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<script setup>
import { ref, watch } from 'vue'

const props = defineProps({
   modelValue: { type: Boolean, default: false },
   title: { type: String, default: 'Confirm' },
   message: { type: String, default: 'Are you sure?' },
   confirmLabel: { type: String, default: 'Confirm' },
   cancelLabel: { type: String, default: 'Cancel' },
 })

const emit = defineEmits(['update:modelValue', 'confirm', 'cancel'])

const visible = ref(false)

watch(() => props.modelValue, (v) => {
  visible.value = v
})

function confirm() {
  emit('update:modelValue', false)
  emit('confirm')
}

function cancel() {
  emit('update:modelValue', false)
  emit('cancel')
}
</script>
