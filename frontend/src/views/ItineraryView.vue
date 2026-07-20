<!-- Itinerari: lista tour multi-giorno e dettaglio tappe. -->
<template>
  <section class="itinerary-view">
    <h2> Itinerari</h2>

    <div v-if="store.loading" class="muted">Caricamento…</div>
    <p v-if="store.error" class="error">{{ store.error }}</p>

    <div v-if="!store.current" class="list">
      <button class="new-btn" @click="showCreate = !showCreate">
        {{ showCreate ? "Annulla" : "+ Nuovo itinerario" }}
      </button>

      <div v-if="showCreate" class="create-form">
        <input v-model="form.name" type="text" placeholder="Nome tour" maxlength="150" />
        <input v-model="form.start_date" type="date" />
        <input v-model="form.end_date" type="date" />
        <button :disabled="!form.name" @click="onCreate">Crea</button>
      </div>

      <ul>
        <li v-for="it in store.itineraries" :key="it.id" @click="open(it.id)">
          <strong>{{ it.name }}</strong>
          <span class="muted" v-if="it.start_date"> · {{ it.start_date }} → {{ it.end_date }}</span>
        </li>
      </ul>
      <p v-if="!store.itineraries.length" class="muted">Nessun itinerario ancora.</p>
    </div>

    <div v-else class="detail">
      <button class="back-btn" @click="store.current = null">← Elenco</button>
      <h3>{{ store.current.itinerary.name }}</h3>
      <p class="muted">Km totali tappe: {{ store.totalKm.toFixed(1) }} km</p>

      <div class="stage-form">
        <input v-model="stage.title" type="text" placeholder="Titolo tappa" maxlength="150" />
        <input v-model.number="stage.distance_km" type="number" min="0" step="0.1" placeholder="Km" />
        <input v-model.number="stage.elevation_gain_m" type="number" min="0" step="1" placeholder="Dislivello m" />
        <button :disabled="!stage.title" @click="onAddStage">+ Tappa</button>
      </div>

      <ol>
        <li v-for="st in store.current.stages" :key="st.id">
          Giorno {{ st.stage_day }} — {{ st.title }}
          <span class="muted" v-if="st.distance_km"> · {{ st.distance_km }} km</span>
          <span class="muted" v-if="st.elevation_gain_m"> · ↑ {{ st.elevation_gain_m }} m</span>
        </li>
      </ol>
      <p v-if="!store.current.stages.length" class="muted">Nessuna tappa.</p>
    </div>
  </section>
</template>

<script setup lang="ts">
import { ref, onMounted } from "vue";
import { useItineraryStore } from "../stores/itinerary";

const store = useItineraryStore();
const showCreate = ref(false);
const form = ref<{ name: string; start_date: string; end_date: string }>({
  name: "",
  start_date: "",
  end_date: "",
});
const stage = ref<{ title: string; distance_km: number | null; elevation_gain_m: number | null }>({
  title: "",
  distance_km: null,
  elevation_gain_m: null,
});

onMounted(() => store.loadList());

async function onCreate() {
  const id = await store.create({ ...form.value });
  if (id !== null) {
    showCreate.value = false;
    form.value = { name: "", start_date: "", end_date: "" };
    await open(id);
  }
}

async function open(id: number) {
  await store.loadOne(id);
}

async function onAddStage() {
  if (!store.current) return;
  const ok = await store.addStage(store.current.itinerary.id, { ...stage.value });
  if (ok) {
    stage.value = { title: "", distance_km: null, elevation_gain_m: null };
  }
}
</script>

<style scoped>
.itinerary-view {
  padding: 16px;
}
.muted {
  color: var(--text-muted);
}
.error {
  color: var(--error);
}
.list ul {
  list-style: none;
  padding: 0;
}
.list li {
  padding: 10px 12px;
  border: 1px solid var(--border);
  border-radius: var(--radius-sm);
  margin-bottom: 8px;
  cursor: pointer;
}
.list li:hover {
  border-color: var(--accent);
}
.create-form,
.stage-form {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin: 12px 0;
}
.create-form input,
.stage-form input {
  background: var(--bg-primary);
  border: 1px solid var(--border);
  border-radius: var(--radius-sm);
  padding: 8px;
  color: var(--text-primary);
}
button {
  background: var(--accent);
  color: #fff;
  border: none;
  border-radius: var(--radius-sm);
  padding: 8px 14px;
  cursor: pointer;
}
.back-btn {
  background: var(--bg-secondary);
  color: var(--text-secondary);
  margin-bottom: 12px;
}
</style>
