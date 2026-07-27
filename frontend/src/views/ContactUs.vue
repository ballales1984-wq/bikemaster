<!--
  Contact and useful resources page.
  Shows support and privacy email addresses, GitHub link, and quick navigation cards
  to Privacy Policy, Terms, Cookie Policy and About Us.
  Layout: grid of info cards and internal links.
-->
<template>
  <div class="contact-page">
    <div class="contact-header">
      <h1>Contact Us</h1>
      <p class="subtitle">
        Do you have questions, suggestions or want to collaborate?
      </p>
    </div>

    <div class="contact-info-grid">
      <div class="info-card">
        <h3>Email</h3>
        <p>
          <a href="mailto:support@bikemaster.app">support@bikemaster.app</a>
        </p>
        <p class="text-muted">Technical support and general information</p>
      </div>
      <div class="info-card">
        <h3>Privacy</h3>
        <p>
          <a href="mailto:privacy@bikemaster.app">privacy@bikemaster.app</a>
        </p>
        <p class="text-muted">Personal data protection requests</p>
      </div>
      <div class="info-card">
        <h3>GitHub</h3>
        <p>
          <a
            href="https://github.com/ballales1984-wq/bikemaster"
            target="_blank"
            rel="noopener"
            >github.com/ballales1984-wq/bikemaster</a
          >
        </p>
        <p class="text-muted">
          Report bugs, request features or contribute to the code
        </p>
      </div>
    </div>

    <div class="site-links-section">
      <h2>Useful Resources</h2>
      <div class="links-grid">
        <RouterLink to="/privacy" class="link-card">
          <span class="link-icon"></span>
          <span>Privacy Policy</span>
        </RouterLink>
        <RouterLink to="/terms" class="link-card">
          <span class="link-icon"></span>
          <span>Termini di Servizio</span>
        </RouterLink>
        <RouterLink to="/cookies" class="link-card">
          <span class="link-icon"></span>
          <span>Cookie Policy</span>
        </RouterLink>
        <RouterLink to="/about" class="link-card">
          <span class="link-icon"></span>
          <span>Chi Siamo</span>
        </RouterLink>
      </div>
    </div>

    <div class="login-cta">
      <RouterLink to="/" class="btn btn-primary">
        Accedi a BikeMaster
      </RouterLink>
    </div>
  </div>
</template>

<script setup lang="ts">
import { RouterLink } from "vue-router";
</script>

<style scoped>
.contact-page {
  max-width: 900px;
  margin: 0 auto;
  padding: 2rem;
}
.contact-header {
  text-align: center;
  margin-bottom: 2rem;
}
.contact-header h1 {
  font-size: 2rem;
  margin-bottom: 0.5rem;
}
.subtitle {
  color: #888;
  font-size: 1rem;
}
.contact-info-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
  gap: 1.2rem;
  margin-bottom: 2.5rem;
}
.info-card {
  background: #1a1a1a;
  padding: 1.5rem;
  border-radius: 8px;
  border: 1px solid #333;
  text-align: center;
}
.info-card h3 {
  margin-bottom: 0.6rem;
  font-size: 1rem;
}
.info-card p {
  margin: 0.2rem 0;
  font-size: 0.9rem;
  color: #bbb;
}
.text-muted {
  color: #777 !important;
  font-size: 0.8rem !important;
}
.site-links-section h2 {
  text-align: center;
  font-size: 1.3rem;
  margin-bottom: 1rem;
  padding-bottom: 0.5rem;
  border-bottom: 2px solid #333;
}
.links-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
  gap: 1rem;
}
.link-card {
  display: flex;
  align-items: center;
  gap: 0.6rem;
  padding: 1rem;
  background: #1a1a1a;
  border: 1px solid #333;
  border-radius: 8px;
  text-decoration: none;
  color: #fff;
  transition:
    border-color 0.2s,
    transform 0.1s;
  font-size: 0.95rem;
}
.link-card:hover {
  border-color: #42b983;
  transform: translateY(-2px);
}
.link-icon {
  font-size: 1.2rem;
}
a {
  color: #42b983;
}

.login-cta {
  text-align: center;
  margin-top: 2rem;
}

.btn.btn-primary {
  display: inline-block;
  padding: 0.75rem 2rem;
  background: #42b983;
  color: #fff;
  text-decoration: none;
  border-radius: 6px;
  font-weight: 600;
  transition: background 0.2s;
}

.btn.btn-primary:hover {
  background: #349a6e;
}
</style>
