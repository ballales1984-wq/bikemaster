// Vercel Serverless Function used as a cron target.
// Vercel's crons cannot run inside a pure Vite frontend, so we expose this
// function at /api/cron (the default Vercel api directory at the repo root).
//
// Role: keep-alive ping to the Render-hosted FastAPI backend (/api/v1/health)
// so the free tier instance does not go to sleep. Swap BACKEND_URL to point
// elsewhere, or change the target path to hit another public endpoint.

export default async function handler(request) {
  const authHeader = request.headers.get("Authorization");
  const cronSecret = process.env.CRON_SECRET;

  if (!cronSecret || authHeader !== `Bearer ${cronSecret}`) {
    return new Response("Unauthorized", { status: 401 });
  }

  const backendUrl = (process.env.BACKEND_URL || "https://bikemaster-api.onrender.com").replace(/\/+$/, "");
  const target = `${backendUrl}/api/v1/health`;

  try {
    const res = await fetch(target, {
      method: "GET",
      headers: { "user-agent": "bikemaster-vercel-cron" },
    });
    const body = await res.text();
    return new Response(
      JSON.stringify({ ok: res.ok, status: res.status, backend: target, body }),
      { status: 200, headers: { "content-type": "application/json" } },
    );
  } catch (err) {
    return new Response(
      JSON.stringify({ ok: false, error: String(err), backend: target }),
      { status: 502, headers: { "content-type": "application/json" } },
    );
  }
}
