<template>
  <div class="metabolism-panel">
    <h3>Profilo metabolico</h3>
    <div class="kpi-grid">
      <div class="kpi">
        <span class="kpi-label">BMR</span>
        <span class="kpi-value">{{ Math.round(bmr) }} kcal</span>
        <span class="kpi-note">Metabolismo basale</span>
      </div>
      <div class="kpi">
        <span class="kpi-label">TDEE</span>
        <span class="kpi-value">{{ Math.round(tdee) }} kcal</span>
        <span class="kpi-note">Dispendio giornaliero</span>
      </div>
      <div class="kpi">
        <span class="kpi-label">Intake</span>
        <span class="kpi-value">{{ Math.round(intake) }} kcal</span>
        <span class="kpi-note">Cibo oggi</span>
      </div>
      <div class="kpi" :class="{ 'kpi--positive': balance > 0, 'kpi--negative': balance < 0 }">
        <span class="kpi-label">Bilancio</span>
        <span class="kpi-value">{{ Math.round(balance) }} kcal</span>
        <span class="kpi-note">{{ balance > 0 ? 'Surplus' : balance < 0 ? 'Deficit' : 'Pareggio' }}</span>
      </div>
    </div>
    <form class="form-grid" @submit.prevent="save">
      <div class="form-group">
        <label for="sex">Sesso</label>
        <select id="sex" v-model="form.sex">
          <option value="male">Uomo</option>
          <option value="female">Donna</option>
        </select>
      </div>
      <div class="form-group">
        <label for="bmr_formula">Formula BMR</label>
        <select id="bmr_formula" v-model="form.bmr_formula">
          <option value="mifflin">Mifflin-St Jeor</option>
          <option value="cunningham">Cunningham</option>
        </select>
      </div>
      <div class="form-group">
        <label for="activity_level">Attivita'</label>
        <select id="activity_level" v-model="form.activity_level">
          <option value="sedentary">Sedentario</option>
          <option value="light">Leggero</option>
          <option value="moderate">Moderato</option>
          <option value="active">Attivo</option>
          <option value="very_active">Molto attivo</option>
        </select>
      </div>
      <div class="form-actions">
        <button class="btn btn-primary" type="submit" :disabled="saving">
          {{ saving ? "Salvataggio..." : "Salva profilo" }}
        </button>
      </div>
    </form>
  </div>
</template>

<script setup lang="ts">
import { computed, reactive, watch } from "vue";
import { useMetabolismStore } from "../stores/metabolism";
import { useToast } from "../composables/useToast";

const store = useMetabolismStore();
const toast = useToast();

const bmr = computed(() => store.profile?.bmr_kcal ?? 0);
const tdee = computed(() => store.profile?.tdee_kcal ?? 0);
const intake = computed(() => store.intake);
const balance = computed(() => store.balance);
const saving = computed(() => store.saving);

const form = reactive({
  sex: store.profile?.sex ?? "male",
  bmr_formula: store.profile?.bmr_formula ?? "mifflin",
  activity_level: store.profile?.activity_level ?? "moderate",
});

watch(
  () => store.profile,
  (p) => {
    if (p) {
      form.sex = p.sex ?? "male";
      form.bmr_formula = p.bmr_formula ?? "mifflin";
      form.activity_level = p.activity_level ?? "moderate";
    }
  },
  { immediate: true }
);

async function save() {
  try {
    await store.updateProfile({
      sex: form.sex,
      bmr_formula: form.bmr_formula,
      activity_level: form.activity_level,
    });
    toast.add("Profilo metabolico salvato", "success");
  } catch {
    toast.add("Errore salvataggio profilo", "error");
  }
}
</script>

<style scoped>
.kpi-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(140px, 1fr));
  gap: 1rem;
  margin-bottom: 1.5rem;
}
.kpi {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 0.75rem;
  padding: 1rem;
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
}
.kpi-label {
  font-size: 0.75rem;
  color: var(--text-muted);
  text-transform: uppercase;
  letter-spacing: 0.05em;
}
.kpi-value {
  font-size: 1.5rem;
  font-weight: 700;
}
.kpi-note {
  font-size: 0.75rem;
  color: var(--text-muted);
}
.kpi--positive {
  border-color: #16a34a;
}
.kpi--negative {
  border-color: #dc2626;
}
.form-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
  gap: 1rem;
  align-items: end;
}
.form-actions {
  grid-column: 1 / -1;
}
</style>
