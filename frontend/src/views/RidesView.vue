<template>
  <div>
    <div class="welcome-card">
      <div>
        <h2>👋 Bentornato in BikeMaster</h2>
        <p>
          Monitora le tue performance, pianifica gli allenamenti e raggiungi i
          tuoi obiettivi ciclistici.
        </p>
      </div>
      <div class="welcome-actions">
        <router-link
to="/track" class="btn btn-primary"
>
          📍 Traccia Uscita
        </router-link>
        <router-link
to="/calendar" class="btn btn-secondary"
>
          📅 Pianifica
        </router-link>
        <router-link
to="/coach" class="btn btn-secondary"
>
          🧠 AI Coach
        </router-link>
      </div>
    </div>
    <RidesPanel @summary-change="$emit('summary-change')" />
  </div>
</template>

<script setup>
import RidesPanel from "../components/RidesPanel.vue";
</script>
