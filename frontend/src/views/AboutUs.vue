<!--
  Institutional "About Us" page.
  Describes BikeMaster's mission, main features, tech stack
  and values of the open-source project.
  Includes links to Contact Us and the login area.
-->
<template>
  <div class="about-page">
    <div class="about-header">
      <h1> BikeMaster</h1>
      <p class="tagline">Cycling Performance Intelligence</p>
    </div>

    <div class="about-content">
      <section class="hero">
        <h2>About Us</h2>
        <p>
          BikeMaster is an open-source project dedicated to advanced cycling
          performance analysis. Our mission is to provide professional tools
          for cyclists of every level, from beginners to competitive
          athletes, to understand and improve their performance
          through data, algorithms and artificial intelligence.
        </p>
      </section>

      <section class="features">
        <h2>What We Do</h2>
        <div class="feature-grid">
          <div class="feature-card">
            <h3> Performance Analysis</h3>
            <p>
              Complete analysis of rides with advanced metrics: Normalized
              Power, TSS, FTP, Critical Power, CTL/ATL/TSB.
            </p>
          </div>
          <div class="feature-card">
            <h3> AI Coach</h3>
            <p>
              Personalized training and recovery advice via LLM
              models and knowledge based on scientific data.
            </p>
          </div>
          <div class="feature-card">
            <h3> Interactive Maps</h3>
            <p>
              Route visualization colored by speed, GPS heatmaps, and
              road safety analysis.
            </p>
          </div>
          <div class="feature-card">
            <h3> Mobile Tracking</h3>
            <p>
              Ride recording directly from your Android phone with
              foreground GPS service.
            </p>
          </div>
          <div class="feature-card">
            <h3> Integrations</h3>
            <p>
              Sync with Strava, Garmin Connect and Google Fit to
              import all your activities.
            </p>
          </div>
          <div class="feature-card">
            <h3> Benchmarking</h3>
            <p>
              Compare your performance with athletes in your category to
              understand your level.
            </p>
          </div>
        </div>
      </section>

      <section class="tech">
        <h2>Technology</h2>
        <p>We build BikeMaster with modern, open-source technologies:</p>
        <ul>
          <li><strong>Backend:</strong> FastAPI, Python 3.11+</li>
          <li><strong>Frontend:</strong> Vue 3, TypeScript, Vite</li>
          <li><strong>Database:</strong> SQLite / PostgreSQL with SQLAlchemy</li>
          <li><strong>AI/ML:</strong> NumPy, Pandas, SciPy, Groq LLM</li>
          <li><strong>Maps:</strong> Leaflet.js, Folium, OpenStreetMap</li>
          <li><strong>Mobile:</strong> Android Kotlin, Capacitor</li>
        </ul>
      </section>

      <section class="values">
        <h2>Our Values</h2>
        <ul>
          <li>
            <strong>Open Source:</strong> the code is public on GitHub under
            MIT license
          </li>
          <li>
            <strong>Privacy First:</strong> your data is yours, we do not
            sell it to third parties
          </li>
          <li>
            <strong>Community Driven:</strong> we build with and for the cycling
            community
          </li>
          <li>
            <strong>Scientific Approach:</strong> algorithms based on physiological
            and scientific principles
          </li>
        </ul>
      </section>

      <section class="cta">
        <p>Want to contribute or learn more?</p>
        <RouterLink
to="/contact" class="cta-button"> Contact Us </RouterLink>
      </section>

      <div class="login-cta">
        <RouterLink to="/" class="btn btn-secondary">
           Login to BikeMaster
        </RouterLink>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { RouterLink } from "vue-router";
</script>

<style scoped>
.about-page {
  max-width: 900px;
  margin: 0 auto;
  padding: 2rem;
}
.about-header {
  text-align: center;
  margin-bottom: 2rem;
}
.about-header h1 {
  font-size: 2.5rem;
  margin-bottom: 0.5rem;
}
.tagline {
  color: #888;
  font-size: 1.1rem;
}
.about-content section {
  margin-bottom: 2.5rem;
}
.about-content h2 {
  border-bottom: 2px solid #42b983;
  padding-bottom: 0.5rem;
  margin-bottom: 1rem;
  font-size: 1.4rem;
}
.about-content p {
  line-height: 1.8;
  margin-bottom: 0.75rem;
}
.feature-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
  gap: 1rem;
  margin-top: 1rem;
}
.feature-card {
  background: #1a1a1a;
  padding: 1.2rem;
  border-radius: 8px;
  border: 1px solid #333;
}
.feature-card h3 {
  margin-bottom: 0.5rem;
  font-size: 1.1rem;
}
.feature-card p {
  font-size: 0.9rem;
  color: #bbb;
  margin: 0;
}
.tech ul,
.values ul {
  margin-left: 1.5rem;
}
.tech li,
.values li {
  line-height: 1.8;
  margin-bottom: 0.4rem;
}
.values li strong {
  color: #42b983;
}
.cta {
  text-align: center;
  padding: 2rem;
  background: #1a1a1a;
  border-radius: 8px;
  border: 1px solid #333;
}
.cta-button {
  display: inline-block;
  margin-top: 1rem;
  padding: 0.75rem 2rem;
  background: #42b983;
  color: #fff;
  text-decoration: none;
  border-radius: 6px;
  font-weight: bold;
  transition: background 0.2s;
}
.cta-button:hover {
  background: #349a6e;
}
a {
  color: #42b983;
}
.login-cta {
  text-align: center;
  margin-top: 1rem;
}
.btn.btn-secondary {
  display: inline-block;
  padding: 0.75rem 2rem;
  background: #2a2a2a;
  color: #fff;
  text-decoration: none;
  border-radius: 6px;
  font-weight: 600;
  transition: background 0.2s;
}
.btn.btn-secondary:hover {
  background: #3a3a3a;
}
</style>
