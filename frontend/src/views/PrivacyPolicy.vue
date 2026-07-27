<!--
  Static Privacy Policy page.
  Complete information on personal data processing, GDPR, security,
  sharing with third parties and user rights.
  Layout: centered container with header, formatted text and link to Cookie Policy.
-->
<template>
  <div class="legal-page">
    <div class="legal-header">
      <h1>Privacy Policy</h1>
      <p class="last-updated">Last updated: June 2025</p>
    </div>

    <div class="legal-content">
      <h2>1. Data Controller</h2>
      <p>
        The data controller of the personal data collected through BikeMaster
        is:
      </p>
      <ul>
        <li><strong>Company:</strong> BikeMaster Team</li>
        <li><strong>Email:</strong> privacy@bikemaster.app</li>
      </ul>

      <h2>2. Types of Data Collected</h2>
      <p>
        Through the use of BikeMaster, we collect the following categories of
        data:
      </p>
      <ul>
        <li>
          <strong>Navigation data:</strong> IP address, browser type, operating
          system, log data
        </li>
        <li>
          <strong>User personal data:</strong> name, email, age, weight, height,
          medical data voluntarily provided in the athlete profile
        </li>
        <li>
          <strong>GPS and physical activity data:</strong> geographic
          coordinates, route track, speed, altitude, heart rate, power, cadence,
          distance, elevation
        </li>
        <li>
          <strong>Geolocation data:</strong> real-time position during GPS
          tracking from phone
        </li>
        <li>
          <strong>Data from external services:</strong> activity data from
          Strava, Garmin Connect, Google Fit (only if authorized by the user)
        </li>
        <li>
          <strong>Access credentials:</strong> username and password (stored in
          encrypted form)
        </li>
      </ul>

      <h2>3. Purposes of Processing</h2>
      <p>Personal data is processed for the following purposes:</p>
      <ul>
        <li>
          <strong>Service provision:</strong> cycling performance analysis,
          metric calculation (calories, TSS, CTL/ATL/TSB), map and report
          generation
        </li>
        <li>
          <strong>AI Coach features:</strong> personalized training and recovery
          advice
        </li>
        <li>
          <strong>Authentication:</strong> account management and access to the
          service
        </li>
        <li>
          <strong>Integrations:</strong> synchronization with external services
          upon consent
        </li>
        <li>
          <strong>Service improvement:</strong> aggregated and anonymized
          statistics to improve features
        </li>
        <li>
          <strong>Security:</strong> protection from unauthorized access and
          anomaly detection
        </li>
      </ul>

      <h2>4. Legal Basis of Processing</h2>
      <ul>
        <li>
          <strong>Contract performance:</strong> processing necessary to provide
          the requested service (Art. 6, par. 1, lett. b GDPR)
        </li>
        <li>
          <strong>Consent:</strong> processing of health data and real-time
          geolocation (Art. 6, par. 1, lett. a GDPR)
        </li>
        <li>
          <strong>Legitimate interest:</strong> data security, aggregate
          statistics (Art. 6, par. 1, lett. f GDPR)
        </li>
      </ul>

      <h2>5. Sensitive Data and Geolocation</h2>
      <p>The service collects potentially sensitive data including:</p>
      <ul>
        <li>
          <strong>Health data:</strong> heart rate, fatigue data, performance
          scores (Art. 9 GDPR)
        </li>
        <li>
          <strong>Geolocation:</strong> continuous GPS position during tracking
          from mobile device
        </li>
      </ul>
      <p>
        This data is processed exclusively upon explicit consent and is used
        only for the purposes indicated in this policy.
      </p>

      <h2>6. Data Sharing and Third Parties</h2>
      <p>
        Personal data is not transferred to third parties for a fee. It is
        shared exclusively with:
      </p>
      <ul>
        <li><strong>Strava:</strong> upon user OAuth2 authorization</li>
        <li><strong>Garmin Connect:</strong> upon user OAuth2 authorization</li>
        <li><strong>Google Fit:</strong> upon user OAuth2 authorization</li>
        <li>
          <strong>Google Maps / OpenStreetMap:</strong> geolocation data for map
          rendering
        </li>
        <li>
          <strong>Groq API:</strong> training data for the AI Coach (does not
          share identifying data)
        </li>
        <li>
          <strong>OpenAI API:</strong> embeddings for semantic search in the
          Knowledge Base (anonymized data)
        </li>
      </ul>

      <h2>7. Data Retention</h2>
      <ul>
        <li>
          <strong>GPS tracking data:</strong> retained until deleted by the user
        </li>
        <li>
          <strong>Athlete profile data:</strong> retained until account deletion
        </li>
        <li>
          <strong>Access data (JWT):</strong> retained for the duration of the
          session
        </li>
        <li>
          <strong>OAuth tokens:</strong> retained until explicit revocation
        </li>
      </ul>

      <h2>8. User Rights</h2>
      <p>Under Articles 15-22 of the GDPR, the user has the right to:</p>
      <ul>
        <li>Access their personal data</li>
        <li>Request correction or update</li>
        <li>Request deletion (right to be forgotten)</li>
        <li>Restrict processing</li>
        <li>Object to processing</li>
        <li>Data portability</li>
        <li>Withdraw consent at any time</li>
      </ul>
      <p>To exercise these rights: <strong>privacy@bikemaster.app</strong></p>

      <h2>9. Security Measures</h2>
      <ul>
        <li>Password encryption with bcrypt</li>
        <li>JWT tokens with automatic refresh</li>
        <li>Rate limiting for API protection</li>
        <li>HTTPS for all communications</li>
        <li>Database with periodic backups</li>
        <li>Minimum necessary data access (least privilege)</li>
      </ul>

      <h2>10. Cookies and Similar Technologies</h2>
      <p>
        For detailed information on cookies, see the
        <RouterLink to="/cookies"> Cookie Policy </RouterLink>.
      </p>

      <h2>11. Changes to This Policy</h2>
      <p>
        Any changes will be communicated through the service or via email to
        registered users. We recommend consulting this page periodically.
      </p>

      <h2>12. Supervisory Authority</h2>
      <p>
        In case of no response or dissatisfaction, you may file a complaint with
        the Italian Data Protection Authority at
        <a href="https://www.garanteprivacy.it" target="_blank" rel="noopener"
          >www.garanteprivacy.it</a
        >.
      </p>
    </div>

    <div class="cta-section">
      <RouterLink to="/" class="btn btn-primary"> Torna all'Accedi </RouterLink>
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
