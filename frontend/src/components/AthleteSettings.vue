<template>
  <section>
    <div class="panel">
      <h2>👤 Profilo Atleta</h2>
      <div v-if="loading" class="loading-text">Caricamento...</div>
      <form v-else @submit.prevent="save">
      <div class="form-row">
        <label for="athlete-name">Nome:</label>
        <input id="athlete-name" v-model="form.name" required />
      </div>
      <div class="form-row">
        <label for="athlete-age">Età:</label>
        <input id="athlete-age" v-model.number="form.age" type="number" />
      </div>
      <div class="form-row">
        <label for="athlete-weight">Peso (kg):</label>
        <input id="athlete-weight" v-model.number="form.weight_kg" type="number" step="0.1" />
      </div>
      <div class="form-row">
        <label for="athlete-height">Altezza (cm):</label>
        <input id="athlete-height" v-model.number="form.height_cm" type="number" />
      </div>
      <div class="form-row">
        <label for="athlete-years">Anni attività:</label>
        <input id="athlete-years" v-model.number="form.years_active" type="number" />
      </div>
      <div class="form-row">
        <label for="athlete-goals">Obiettivo:</label>
        <input id="athlete-goals" v-model="form.goals" placeholder="Gran Fondo, criterium, etc." />
      </div>
        <button class="btn btn-primary" type="submit">Salva</button>
      </form>
    </div>
  </section>
</template>

<script setup>
import { ref, onMounted } from "vue"
import { apiGet, apiPut, apiPost } from "../utils/api"

const loading = ref(true)
const athleteId = ref(null)
const form = ref({
  name: "",
  age: 30,
  weight_kg: 70,
  height_cm: 175,
  years_active: 3,
  goals: ""
})

async function load() {
  loading.value = true
  try {
    const data = await apiGet("/api/v1/athletes")
    const athletes = data.athletes || []
    if (athletes.length > 0) {
      athleteId.value = athletes[athletes.length - 1].id
      const athlete = await apiGet(`/api/v1/athletes/${athleteId.value}`)
      form.value = { ...form.value, ...athlete }
    }
  } finally {
    loading.value = false
  }
}

async function save() {
  if (athleteId.value) {
    await apiPut(`/api/v1/athletes/${athleteId.value}`, {
      name: form.value.name,
      age: form.value.age,
      weight_kg: form.value.weight_kg,
      goals: form.value.goals
    })
  } else {
    const result = await apiPost("/api/v1/athletes", form.value)
    athleteId.value = result.id
  }
}

onMounted(() => {
  load()
})
</script>
