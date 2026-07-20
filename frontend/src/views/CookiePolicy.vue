<!--
  Static Cookie Policy page.
  Explains the types of cookies used (technical, analytics, preferences),
  the third parties involved and how to manage cookies in the browser.
  Includes technical cookies table and notes for the mobile app.
-->
<template>
  <div class="legal-page">
    <div class="legal-header">
      <h1>Cookie Policy</h1>
      <p class="last-updated">Last updated: June 2025</p>
    </div>

    <div class="legal-content">
      <h2>1. What Are Cookies</h2>
      <p>
        Cookies are small text files stored on the user's device
        while browsing a website. Cookies allow
        the site to recognize the user and store certain information
        to improve the user experience.
      </p>

      <h2>2. Types of Cookies Used</h2>
      <h3>2.1 Technical Cookies (Strictly Necessary)</h3>
      <p>
        These cookies are essential for the proper functioning of the BikeMaster
        service:
      </p>
      <table class="cookie-table">
        <thead>
          <tr>
            <th>Name</th>
            <th>Purpose</th>
            <th>Duration</th>
          </tr>
        </thead>
        <tbody>
          <tr>
            <td><code>access_token</code></td>
            <td>User JWT authentication</td>
            <td>Browser session</td>
          </tr>
          <tr>
            <td><code>refresh_token</code></td>
            <td>Automatic session renewal</td>
            <td>7 days</td>
          </tr>
          <tr>
            <td><code>bikemaster_session</code></td>
            <td>User session state management</td>
            <td>Browser session</td>
          </tr>
        </tbody>
      </table>

      <h3>2.2 Analytics Cookies</h3>
      <p>
        Used to understand how users interact with the service
        (anonymized or aggregated):
      </p>
      <ul>
        <li>
          <strong>Usage statistics:</strong> pages visited, session
          duration, errors encountered
        </li>
        <li>
          <strong>Performance:</strong> loading times, API calls,
          system metrics
        </li>
      </ul>

      <h3>2.3 Preference Cookies</h3>
      <ul>
        <li>
          <strong>Dark/light theme:</strong> interface theme preference
        </li>
        <li>
          <strong>Dashboard layout:</strong> preferred panel configuration
        </li>
        <li><strong>Units:</strong> km/mi, °C/°F, watts/kg</li>
      </ul>

      <h2>3. Third-Party Cookies</h2>
      <p>
        Some cookies may be set by third-party services integrated into the
        service:
      </p>
      <ul>
        <li>
          <strong>Google Maps / OpenStreetMap:</strong> for displaying
          routes on maps
        </li>
        <li>
          <strong>Chart.js:</strong> no own cookies, data handled
          locally
        </li>
      </ul>
      <p>
        These third parties have their own privacy policies, not controlled by
        BikeMaster.
      </p>

      <h2>4. Cookie Management and Disabling</h2>
      <p>
        The user can manage cookies directly through the browser
        settings:
      </p>
      <ul>
        <li>
          <strong>Chrome:</strong> Settings → Privacy and security → Cookies and
          other site data
        </li>
        <li>
          <strong>Firefox:</strong> Settings → Privacy and security → Cookies
          and site data
        </li>
        <li>
          <strong>Safari:</strong> Preferences → Privacy → Manage websites
        </li>
        <li>
          <strong>Edge:</strong> Settings → Privacy, search and services →
          Cookies
        </li>
      </ul>
      <p>
        <strong>Note:</strong> Disabling technical cookies may
        impair the functioning of the service and prevent access
        to the account.
      </p>

      <h2>5. Notes for the Mobile App (Android)</h2>
      <p>
        The BikeMaster Android mobile application, installed via APK, does
        not use traditional cookies. Instead, it uses:
      </p>
      <ul>
        <li>
          <strong>Android Shared Preferences:</strong> for session data and
          preferences
        </li>
        <li><strong>Local Storage:</strong> for cache and offline data</li>
      </ul>
      <p>
        Background GPS tracking requires location authorization,
        managed by the Android operating system.
      </p>

      <h2>6. Alternative Tracking Tools</h2>
      <p>In addition to cookies, BikeMaster may use:</p>
      <ul>
        <li>
          <strong>Local Storage:</strong> for data persistence on the
          browser
        </li>
        <li>
          <strong>Session Storage:</strong> for temporary session data
        </li>
        <li>
          <strong>IndexedDB:</strong> for advanced caching of activity data
        </li>
      </ul>

      <h2>7. Cookie Policy Updates</h2>
      <p>
        Any changes to this policy will be published on this
        page. We recommend consulting it periodically.
      </p>

      <h2>8. Contact</h2>
      <p>
        For questions about cookies or tracking practices:
        <a href="mailto:privacy@bikemaster.app">privacy@bikemaster.app</a>
      </p>
    </div>

    <div class="cta-section">
      <RouterLink to="/" class="btn btn-primary">
         Back to Login
      </RouterLink>
    </div>
  </div>
</template>

<script setup lang="ts">
import { RouterLink } from "vue-router";
</script>

<style scoped>
.legal-page {
  max-width: 800px;
  margin: 0 auto;
  padding: 2rem;
}
.legal-header {
  text-align: center;
  margin-bottom: 2rem;
  padding-bottom: 1rem;
  border-bottom: 2px solid #333;
}
.legal-header h1 {
  font-size: 1.8rem;
  margin-bottom: 0.5rem;
}
.last-updated {
  color: #888;
  font-size: 0.9rem;
}
.legal-content h2 {
  margin-top: 2rem;
  padding-bottom: 0.5rem;
  border-bottom: 1px solid #333;
  font-size: 1.3rem;
}
.legal-content h3 {
  margin-top: 1.5rem;
  font-size: 1.1rem;
  color: #ccc;
}
.legal-content p {
  line-height: 1.7;
  margin: 0.75rem 0;
}
.legal-content ul {
  margin: 0.75rem 0 0.75rem 1.5rem;
}
.legal-content li {
  line-height: 1.7;
  margin-bottom: 0.4rem;
}
.cookie-table {
  width: 100%;
  border-collapse: collapse;
  margin: 1rem 0;
}
.cookie-table th,
.cookie-table td {
  border: 1px solid #444;
  padding: 0.6rem;
  text-align: left;
}
.cookie-table th {
  background: #2a2a2a;
}
.cookie-table code {
  background: #2a2a2a;
  padding: 0.2rem 0.4rem;
  border-radius: 3px;
  font-size: 0.9rem;
}
a {
  color: #42b983;
}
.cta-section {
  text-align: center;
  margin: 2rem 0 1rem;
}
.btn {
  display: inline-block;
  padding: 10px 24px;
  background: #42b983;
  color: #fff;
  text-decoration: none;
  border-radius: 6px;
  font-weight: 600;
  transition: background 0.2s;
}
.btn:hover {
  background: #349a6e;
}
</style>
