import { describe, expect, it, vi, beforeEach, afterEach } from "vitest";

// Voice coach command parsing is exported as a pure function and is safe to
// test without a DOM.
import { useVoiceCoach } from "./useVoiceCoach";

describe("useVoiceCoach command parsing", () => {
  it("parses Italian status command", () => {
    const { parseCommand } = useVoiceCoach("it");
    expect(parseCommand("Come sto andando?").command).toBe("status");
  });

  it("parses stop command (EN)", () => {
    const { parseCommand } = useVoiceCoach("en");
    expect(parseCommand("Stop").command).toBe("stop");
  });

  it("parses pause command (IT)", () => {
    const { parseCommand } = useVoiceCoach("it");
    expect(parseCommand("Metti in pausa").command).toBe("pause");
  });

  it("parses resume command (EN)", () => {
    const { parseCommand } = useVoiceCoach("en");
    expect(parseCommand("continue").command).toBe("resume");
  });

  it("returns unknown for unrecognized text", () => {
    const { parseCommand } = useVoiceCoach("it");
    expect(parseCommand("che bel tempo oggi").command).toBe("unknown");
  });
});

describe("useVoiceCoach speech support flags", () => {
  beforeEach(() => {
    globalThis.window = { speechSynthesis: undefined, location: { href: "" } };
    delete globalThis.window.SpeechRecognition;
    delete globalThis.window.webkitSpeechRecognition;
  });
  afterEach(() => {
    delete globalThis.window;
  });

  it("exposes boolean support flags", () => {
    const v = useVoiceCoach("it");
    expect(typeof v.ttsSupported.value).toBe("boolean");
    expect(typeof v.sttSupported.value).toBe("boolean");
  });

  it("renders a voice cue via speak without throwing when unsupported", () => {
    const v = useVoiceCoach("it");
    // No speechSynthesis in this environment; speak() should be a no-op.
    expect(() => v.speak("Inizia riscaldamento")).not.toThrow();
  });
});
