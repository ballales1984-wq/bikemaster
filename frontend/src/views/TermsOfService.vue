<!--
  Static Terms of Service page.
  Contains the legal regulatory sections for the use of BikeMaster.
  Layout: centered container with header, formatted text and links to Privacy/Cookies.
-->
<template>
  <div class="legal-page">
    <div class="legal-header">
      <h1>Termini di Servizio</h1>
      <p class="last-updated">Last updated: August 2026</p>
    </div>

    <div class="legal-content">
      <h2>1. Acceptance of Terms</h2>
      <p>
        By using BikeMaster, the user fully accepts these Terms of Service. If
        you do not accept the terms, please do not use the service.
      </p>

      <h2>2. Service Description</h2>
      <p>
        BikeMaster is an intelligent cycling performance analysis system that
        allows you to:
      </p>
      <ul>
        <li>Import GPX and FIT files of cycling rides</li>
        <li>Analyze power, speed, elevation and calories metrics</li>
        <li>Receive personalized advice via AI Coach</li>
        <li>View routes on interactive maps</li>
        <li>
          Sync activities with third-party services (Strava, Garmin, Google Fit)
        </li>
        <li>Track rides in real-time from mobile device</li>
      </ul>

      <h2>3. User Account</h2>
      <ul>
        <li>The user is responsible for the security of their credentials</li>
        <li>
          The user must provide accurate and up-to-date information in the
          athlete profile
        </li>
        <li>
          Each user is responsible for all activities carried out through their
          own account
        </li>
        <li>
          Sharing the account with unauthorized third parties is prohibited
        </li>
      </ul>

      <h2>4. User Data and Content</h2>
      <ul>
        <li>The user retains ownership of all uploaded activity data</li>
        <li>
          Granting a limited license to BikeMaster to process and display the
          data
        </li>
        <li>
          Geolocated data is processed in accordance with the Privacy Policy
        </li>
        <li>The user can export or delete their data at any time</li>
      </ul>

      <h2>5. Acceptable Use</h2>
      <p>It is prohibited to:</p>
      <ul>
        <li>Use the service for illegal or unauthorized activities</li>
        <li>Attempt to access other users' data</li>
        <li>
          Perform scraping, crawling or unauthorized automated use of the APIs
        </li>
        <li>Use the service to overload servers with excessive requests</li>
        <li>Upload harmful, offensive or illegal content</li>
      </ul>

      <h2>6. Third-Party Services</h2>
      <p>
        BikeMaster integrates with third-party services (Strava, Garmin Connect,
        Google Fit). The use of such services is governed by their respective
        terms of service. BikeMaster is not responsible for the operation or
        accuracy of data provided by third parties.
      </p>

      <h2>6.1 AI Coach and Automated Decision-Making</h2>
      <p>
        The AI Coach feature uses artificial intelligence to provide training
        and recovery advice. Under the EU AI Act (Regulation (EU) 2024/1689):
      </p>
      <ul>
        <li>
          AI-generated content is always clearly labeled as such (AI Act Article
          50 - Transparency)
        </li>
        <li>
          The AI system is classified as limited-risk and is subject to
          transparency obligations
        </li>
        <li>
          Users have the right to opt out of AI features at any time via
          Settings
        </li>
        <li>
          AI advice is non-binding and does not replace professional coaching or
          medical advice
        </li>
        <li>
          Interaction logs are retained for accountability and audit purposes
        </li>
      </ul>

      <h2>7. Intellectual Property</h2>
      <ul>
        <li>BikeMaster and its logo are property of the development team</li>
        <li>
          All rights to automatically generated content (maps, analyses,
          reports) remain with the user
        </li>
        <li>
          The source code is released under the MIT license (see LICENSE file)
        </li>
      </ul>

      <h2>8. Limitation of Liability</h2>
      <p>BikeMaster is provided "as is". The team does not guarantee:</p>
      <ul>
        <li>The accuracy of calculated sports metrics</li>
        <li>The absence of errors or service interruptions</li>
        <li>Compatibility with all GPS devices and platforms</li>
      </ul>
      <p>
        The service does not replace medical advice or professional coaching.
        The user is responsible for their own physical activities.
      </p>

      <h2>9. Service Changes</h2>
      <p>
        We reserve the right to modify, suspend or discontinue the service at
        any time, with or without notice. We will not be liable to the user or
        third parties for any modifications, suspensions or interruptions.
      </p>

      <h2>10. Termination</h2>
      <p>
        We reserve the right to suspend or terminate access to the service for
        any user who violates these terms, at our sole discretion.
      </p>

      <h2>11. Applicable Law and Jurisdiction</h2>
      <p>
        These terms are governed by Italian law. For any dispute, the court of
        the service owner's residence shall have exclusive jurisdiction.
      </p>

      <h2>12. Contact</h2>
      <p>
        For questions regarding these terms:
        <a href="mailto:support@bikemaster.app">support@bikemaster.app</a>
      </p>

      <h2>13. Integration with Other Policies</h2>
      <ul>
        <li>
          <RouterLink to="/privacy"> Privacy Policy </RouterLink>
        </li>
        <li>
          <RouterLink to="/cookies"> Cookie Policy </RouterLink>
        </li>
      </ul>
    </div>

    <div class="cta-section">
      <RouterLink to="/" class="btn btn-primary"> Back to Login </RouterLink>
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
