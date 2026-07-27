<!--
  Application landing/welcome page.
  Presents the BikeMaster brand, tagline, main features in cards
  and login/registration buttons.
  Style: animated orb background, modern and responsive design.
-->
<template>
  <div class="welcome-page">
    <div class="welcome-bg" aria-hidden="true">
      <span class="orb orb-1" />
      <span class="orb orb-2" />
      <span class="orb orb-3" />
    </div>

    <div class="welcome-content">
      <header class="welcome-header">
        <div class="brand-mark">
          <span class="brand-emoji" aria-hidden="true"></span>
          <h1 class="brand-name">BikeMaster</h1>
        </div>
        <p class="brand-tagline">Cycling Performance Intelligence</p>
      </header>

      <section class="hero">
        <h2 class="hero-title">Your digital cycling coach</h2>
        <p class="hero-desc">
          Analyze rides, optimize training and reach your goals with scientific
          data and artificial intelligence.
        </p>
      </section>

      <section class="features" aria-label="Main features">
        <div class="feature-card">
          <div class="feature-icon"></div>
          <h3>Analisi Performance</h3>
          <p>
            Normalized Power, TSS, FTP, Critical Power, CTL/ATL/TSB and advanced
            metrics for every ride.
          </p>
        </div>
        <div class="feature-card">
          <div class="feature-icon"></div>
          <h3>AI Coach</h3>
          <p>
            Personalized training and recovery advice based on scientific data
            and LLM models.
          </p>
        </div>
        <div class="feature-card">
          <div class="feature-icon"></div>
          <h3>Integrazioni</h3>
          <p>
            Sync Strava, Garmin Connect and Google Fit to import all your
            activities automatically.
          </p>
        </div>
        <div class="feature-card">
          <div class="feature-icon"></div>
          <h3>Sync Cloud</h3>
          <p>Optional cloud backup and sync, always under your control.</p>
        </div>
      </section>

      <div class="welcome-actions">
        <button class="btn btn-primary btn-lg" @click="goToRegister">
          Get Started
        </button>
        <button class="btn btn-secondary btn-lg" @click="goToLogin">
          Login
        </button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { useRouter } from "vue-router";

const router = useRouter();

function goToLogin() {
  router.push("/");
}

function goToRegister() {
  router.push("/");
}
</script>

<style scoped>
.welcome-page {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 24px;
  position: relative;
  z-index: 1;
}
.welcome-bg {
  position: fixed;
  inset: 0;
  z-index: 0;
  pointer-events: none;
  overflow: hidden;
}
.orb {
  position: absolute;
  border-radius: 50%;
  filter: blur(90px);
  opacity: 0.35;
  will-change: transform;
}
.orb-1 {
  width: 420px;
  height: 420px;
  background: radial-gradient(circle, rgba(0, 255, 204, 0.5), transparent 70%);
  top: -120px;
  left: -100px;
  animation: orbFloat1 18s ease-in-out infinite alternate;
}
.orb-2 {
  width: 360px;
  height: 360px;
  background: radial-gradient(circle, rgba(0, 136, 255, 0.45), transparent 70%);
  bottom: -120px;
  right: -80px;
  animation: orbFloat2 22s ease-in-out infinite alternate;
}
.orb-3 {
  width: 300px;
  height: 300px;
  background: radial-gradient(
    circle,
    rgba(168, 85, 247, 0.35),
    transparent 70%
  );
  top: 40%;
  left: 55%;
  animation: orbFloat3 26s ease-in-out infinite alternate;
}
@keyframes orbFloat1 {
  to {
    transform: translate(60px, 80px) scale(1.15);
  }
}
@keyframes orbFloat2 {
  to {
    transform: translate(-70px, -40px) scale(1.1);
  }
}
@keyframes orbFloat3 {
  to {
    transform: translate(-40px, 60px) scale(0.9);
  }
}
.welcome-content {
  position: relative;
  z-index: 1;
  max-width: 1100px;
  width: 100%;
  text-align: center;
}
.welcome-header {
  margin-bottom: 28px;
}
.brand-mark {
  display: inline-flex;
  align-items: center;
  gap: 12px;
}
.brand-emoji {
  font-size: 2.6rem;
  filter: drop-shadow(0 0 12px rgba(0, 255, 204, 0.45));
  animation: float 4s ease-in-out infinite;
}
@keyframes float {
  0%,
  100% {
    transform: translateY(0);
  }
  50% {
    transform: translateY(-6px);
  }
}
.brand-name {
  font-size: 2.8rem;
  margin: 0;
  background: linear-gradient(135deg, #00ffcc 0%, #0088ff 100%);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
  letter-spacing: -0.02em;
  animation: logoGlow 3s ease-in-out infinite alternate;
}
@keyframes logoGlow {
  from {
    filter: brightness(1);
  }
  to {
    filter: brightness(1.2) drop-shadow(0 0 10px rgba(0, 255, 204, 0.35));
  }
}
.brand-tagline {
  color: #6e7687;
  margin-top: 8px;
  font-size: 0.9rem;
  letter-spacing: 0.18em;
  text-transform: uppercase;
}
.hero {
  margin-bottom: 32px;
}
.hero-title {
  font-size: 1.6rem;
  margin: 0 0 12px;
  color: #f8f9fa;
}
.hero-desc {
  color: #b0b5c1;
  max-width: 680px;
  margin: 0 auto;
  line-height: 1.6;
}
.features {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
  gap: 16px;
  margin-bottom: 32px;
}
.feature-card {
  background: rgba(22, 27, 40, 0.65);
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 16px;
  padding: 18px;
  text-align: left;
  backdrop-filter: blur(12px);
  -webkit-backdrop-filter: blur(12px);
  transition:
    transform 0.2s ease,
    border-color 0.2s ease;
}
.feature-card:hover {
  transform: translateY(-3px);
  border-color: rgba(0, 255, 204, 0.25);
}
.feature-icon {
  font-size: 1.5rem;
  margin-bottom: 10px;
}
.feature-card h3 {
  margin: 0 0 8px;
  font-size: 1.05rem;
  color: #f8f9fa;
}
.feature-card p {
  margin: 0;
  font-size: 0.9rem;
  color: #b0b5c1;
  line-height: 1.5;
}
.welcome-actions {
  display: flex;
  gap: 12px;
  justify-content: center;
  flex-wrap: wrap;
}
.btn {
  border: none;
  cursor: pointer;
  font-weight: 600;
  border-radius: 10px;
  padding: 12px 18px;
  font-size: 1rem;
  transition:
    transform 0.15s ease,
    box-shadow 0.2s ease;
}
.btn:active {
  transform: scale(0.98);
}
.btn-primary {
  background: linear-gradient(135deg, #00ffcc 0%, #0088ff 100%);
  color: #0a0b10;
}
.btn-primary:hover {
  box-shadow: 0 0 24px rgba(0, 255, 204, 0.25);
}
.btn-secondary {
  background: rgba(22, 27, 40, 0.65);
  color: #f8f9fa;
  border: 1px solid rgba(255, 255, 255, 0.12);
}
.btn-secondary:hover {
  border-color: rgba(0, 255, 204, 0.25);
}
.btn-lg {
  padding: 14px 22px;
  font-size: 1.05rem;
  min-width: 160px;
}
@media (max-width: 640px) {
  .brand-name {
    font-size: 2rem;
  }
  .hero-title {
    font-size: 1.25rem;
  }
  .features {
    grid-template-columns: 1fr;
  }
}
@media (prefers-reduced-motion: reduce) {
  .orb,
  .brand-emoji,
  .brand-name {
    animation: none !important;
  }
  .feature-card {
    transition: none;
  }
}
</style>
