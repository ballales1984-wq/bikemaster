export function loadAnalytics() {
  if (typeof window === "undefined") return;

  const raw = localStorage.getItem("bikemaster_consent_v1");
  if (!raw) return;
  try {
    const parsed = JSON.parse(raw);
    if (!parsed.analytics) return;
  } catch {
    return;
  }

  if (document.querySelector('script[src*="googletagmanager.com"]')) return;

  const script = document.createElement("script");
  script.async = true;
  script.src = "https://www.googletagmanager.com/gtag/js?id=G-B5TGQK6KL7";
  document.head.appendChild(script);

  const init = document.createElement("script");
  init.textContent = `
    window.dataLayer = window.dataLayer || [];
    function gtag(){dataLayer.push(arguments);}
    gtag('js', new Date());
    gtag('config', 'G-B5TGQK6KL7');
  `;
  document.head.appendChild(init);
}
