"""Tests for voice coach module."""

from __future__ import annotations

import time

from bike_analyzer.backend.analytics.voice_coach import (
    _AUDIO_CUES,
    _VOICE_INTENT,
    VoiceCoach,
    VoiceCommand,
    VoiceCommandParser,
)


class TestVoiceCommandParser:
    def test_parse_stop_italian(self):
        result = VoiceCommandParser.parse("Ferma la bici", "it")
        assert result.command == VoiceCommand.STOP

    def test_parse_pause_italian(self):
        result = VoiceCommandParser.parse("Pausa un attimo", "it")
        assert result.command == VoiceCommand.PAUSE

    def test_parse_resume_italian(self):
        result = VoiceCommandParser.parse("Riprendi", "it")
        assert result.command == VoiceCommand.RESUME

    def test_parse_status_italian(self):
        result = VoiceCommandParser.parse("Come sto andando?", "it")
        assert result.command == VoiceCommand.STATUS

    def test_parse_status_short(self):
        result = VoiceCommandParser.parse("Come sto", "it")
        assert result.command == VoiceCommand.STATUS

    def test_parse_stop_english(self):
        result = VoiceCommandParser.parse("stop", "en")
        assert result.command == VoiceCommand.STOP

    def test_parse_pause_english(self):
        result = VoiceCommandParser.parse("pause", "en")
        assert result.command == VoiceCommand.PAUSE

    def test_parse_resume_english(self):
        result = VoiceCommandParser.parse("resume", "en")
        assert result.command == VoiceCommand.RESUME

    def test_parse_status_english(self):
        result = VoiceCommandParser.parse("how am i doing", "en")
        assert result.command == VoiceCommand.STATUS

    def test_parse_unknown(self):
        result = VoiceCommandParser.parse("Ciao mondo", "it")
        assert result.command == VoiceCommand.UNKNOWN

    def test_parse_empty_string(self):
        result = VoiceCommandParser.parse("", "it")
        assert result.command == VoiceCommand.UNKNOWN

    def test_parse_case_insensitive(self):
        result = VoiceCommandParser.parse("FERMA", "it")
        assert result.command == VoiceCommand.STOP

    def test_parse_preserves_raw_text(self):
        raw = "Ferma la bici"
        result = VoiceCommandParser.parse(raw, "it")
        assert result.raw == raw
        assert result.language == "it"

    def test_parse_all_intents_have_phrases(self):
        for _, phrases in _VOICE_INTENT.items():
            assert len(phrases) > 0
            for phrase in phrases:
                assert len(phrase) > 0


class TestVoiceCoach:
    def test_default_language_italian(self):
        vc = VoiceCoach()
        assert vc.language == "it"

    def test_english_language(self):
        vc = VoiceCoach(language="en")
        assert vc.language == "en"

    def test_invalid_language_fallback(self):
        vc = VoiceCoach(language="fr")
        assert vc.language == "it"

    def test_can_speak_zone_2(self):
        vc = VoiceCoach()
        can, reason = vc.can_speak(intensity_zone=2)
        assert can is True
        assert reason == "ok"

    def test_can_speak_zone_4_blocked(self):
        vc = VoiceCoach()
        can, reason = vc.can_speak(intensity_zone=4)
        assert can is False
        assert reason == "high intensity (Z4/Z5)"

    def test_can_speak_zone_5_blocked(self):
        vc = VoiceCoach()
        can, reason = vc.can_speak(intensity_zone=5)
        assert can is False
        assert reason == "high intensity (Z4/Z5)"

    def test_can_speak_none_zone_allowed(self):
        vc = VoiceCoach()
        can, reason = vc.can_speak(intensity_zone=None)
        assert can is True

    def test_voice_gap_blocks_speech(self):
        vc = VoiceCoach(last_spoken_at=time.time())
        can, reason = vc.can_speak(intensity_zone=2, now_ts=time.time())
        assert can is False
        assert reason == "voice gap not elapsed"

    def test_voice_gap_allows_after_5_minutes(self):
        now = time.time()
        vc = VoiceCoach(last_spoken_at=now - 310)
        can, reason = vc.can_speak(intensity_zone=2, now_ts=now)
        assert can is True
        assert reason == "ok"

    def test_speak_message_returns_text(self):
        vc = VoiceCoach()
        result = vc.speak_message("training", "test_key")
        assert result is not None
        assert isinstance(result, str)

    def test_speak_message_blocked_during_high_intensity(self):
        vc = VoiceCoach()
        result = vc.speak_message("training", "test_key", intensity_zone=5)
        assert result is None

    def test_speak_message_updates_last_spoken(self):
        vc = VoiceCoach()
        now = time.time()
        vc.speak_message("training", "test_key", now_ts=now)
        assert vc.last_spoken_at == now

    def test_cue_italian(self):
        vc = VoiceCoach(language="it")
        assert vc.cue("warmup") == "Inizia riscaldamento"
        assert vc.cue("cooldown") == "Inizia defaticamento"
        assert vc.cue("five_min_left") == "Mancano 5 minuti"

    def test_cue_english(self):
        vc = VoiceCoach(language="en")
        assert vc.cue("warmup") == "Start warm-up"
        assert vc.cue("cooldown") == "Start cool-down"

    def test_cue_with_variables(self):
        vc = VoiceCoach(language="it")
        assert vc.cue("five_min_left") == "Mancano 5 minuti"

    def test_cue_unknown_key_returns_default(self):
        vc = VoiceCoach(language="it")
        assert vc.cue("nonexistent") == "Continua"

    def test_cue_unknown_key_english(self):
        vc = VoiceCoach(language="en")
        assert vc.cue("nonexistent") == "Keep going"

    def test_status_line_italian(self):
        vc = VoiceCoach(language="it")
        line = vc.status_line(avg_power=200.0, zone=3, hr=150)
        assert "potenza media 200 watt" in line
        assert "zona 3" in line
        assert "frequenza cardiaca 150" in line
        assert "Stai andando" in line

    def test_status_line_english(self):
        vc = VoiceCoach(language="en")
        line = vc.status_line(avg_power=200.0, zone=3, hr=150)
        assert "potenza media 200 watt" in line
        assert "zona 3" in line
        assert "frequenza cardiaca 150" in line
        assert "Stai andando" in line

    def test_status_line_no_values_italian(self):
        vc = VoiceCoach(language="it")
        line = vc.status_line(None, None, None)
        assert line == "Stai andando bene."

    def test_status_line_no_values_english(self):
        vc = VoiceCoach(language="en")
        line = vc.status_line(None, None, None)
        assert line == "Stai andando bene."

    def test_cue_format_exception_returns_raw_text(self):
        vc = VoiceCoach(language="en")
        assert vc.cue("warmup") == "Start warm-up"

    def test_status_line_partial_values(self):
        vc = VoiceCoach(language="it")
        line = vc.status_line(avg_power=180.0, zone=None, hr=None)
        assert "potenza media 180 watt" in line
        assert "Stai andando" in line

    def test_audio_cues_exist_for_both_languages(self):
        assert "it" in _AUDIO_CUES
        assert "en" in _AUDIO_CUES
        assert len(_AUDIO_CUES["it"]) > 0
        assert len(_AUDIO_CUES["en"]) > 0
