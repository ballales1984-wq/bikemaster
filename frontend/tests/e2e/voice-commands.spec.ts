import { test, expect } from "@playwright/test";

const API_BASE = "http://127.0.0.1:8000/api/v1";

test.describe("Voice commands API", () => {
  test("GET /voice/commands returns supported commands", async ({ request }) => {
    const resp = await request.get(`${API_BASE}/voice/commands`);
    expect(resp.status()).toBe(200);
    const data = await resp.json();
    expect(data.commands).toBeInstanceOf(Array);
    expect(data.languages).toContain("it-IT");
    expect(data.languages).toContain("en-US");

    const ids = data.commands.map((c: { id: string }) => c.id);
    expect(ids).toContain("nav.open");
    expect(ids).toContain("weather.load");
    expect(ids).toContain("heatmap.load");
    expect(ids).toContain("badges.load");
    expect(ids).toContain("itinerary.load");
  });

  test("POST /voice/coach/can-speak blocks high intensity zones", async ({
    request,
  }) => {
    const resp = await request.post(`${API_BASE}/voice/coach/can-speak`, {
      data: { intensity_zone: 5, language: "it" },
    });
    expect(resp.status()).toBe(200);
    const data = await resp.json();
    expect(data.can_speak).toBe(false);
    expect(data.reason).toContain("high intensity");
  });

  test("POST /voice/coach/speak returns text for allowed zones", async ({
    request,
  }) => {
    const resp = await request.post(`${API_BASE}/voice/coach/speak`, {
      data: {
        category: "recovery",
        template_key: "default",
        intensity_zone: 1,
        language: "it",
      },
    });
    expect(resp.status()).toBe(200);
    const data = await resp.json();
    expect(data.suppressed).toBe(false);
    expect(typeof data.text).toBe("string");
    expect(data.text.length).toBeGreaterThan(0);
  });

  test("POST /voice/assistant requires non-empty text", async ({ request }) => {
    const resp = await request.post(`${API_BASE}/voice/assistant`, {
      data: { text: "" },
    });
    expect(resp.status()).toBe(400);
  });

  test("GET /voice/tts/audio/{filename} returns 404 for missing files", async ({
    request,
  }) => {
    const resp = await request.get(
      `${API_BASE}/voice/tts/audio/nonexistent_file_404.mp3`,
    );
    expect(resp.status()).toBe(404);
  });
});
