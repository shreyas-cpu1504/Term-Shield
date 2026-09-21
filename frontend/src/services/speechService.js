/**
 * SpeechService - Centralized Web Speech API Coordinator for Term Shield.
 * Guarantees single-utterance playback across the application, manages
 * voice matching, fallback, pause/resume/stop, speed control, and state notification.
 */

import { detectScriptLanguage, SUPPORTED_LANGUAGES } from "./languagePreferences";

class SpeechService {
  constructor() {
    this.currentUtterance = null;
    this.activeId = null;
    this.isPlaying = false;
    this.isPaused = false;
    this.rate = 1.0;
    this.activeLanguage = "en-IN";
    this.isFallbackVoice = false;
    this.listeners = new Set();
    this.voices = [];
    this.isSupported = typeof window !== "undefined" && "speechSynthesis" in window;

    if (this.isSupported) {
      this._loadVoices();
      if (window.speechSynthesis.onvoiceschanged !== undefined) {
        window.speechSynthesis.onvoiceschanged = () => this._loadVoices();
      }
    }
  }

  _loadVoices() {
    if (!this.isSupported) return;
    this.voices = window.speechSynthesis.getVoices() || [];
  }

  /**
   * Subscribe a component to speech state changes.
   */
  subscribe(listener) {
    this.listeners.add(listener);
    // Immediately emit current state to the new listener
    listener(this.getState());
    return () => this.listeners.delete(listener);
  }

  _notify() {
    const state = this.getState();
    this.listeners.forEach((listener) => {
      try {
        listener(state);
      } catch (err) {
        console.error("Error in speech listener:", err);
      }
    });
  }

  getState() {
    return {
      isSupported: this.isSupported,
      activeId: this.activeId,
      isPlaying: this.isPlaying,
      isPaused: this.isPaused,
      rate: this.rate,
      activeLanguage: this.activeLanguage,
      isFallbackVoice: this.isFallbackVoice,
    };
  }

  /**
   * Select best voice for target BCP-47 language tag.
   */
  _findBestVoice(targetLang) {
    if (!this.voices.length) {
      this._loadVoices();
    }

    if (!this.voices.length) {
      return { voice: null, isFallback: true };
    }

    const langLower = targetLang.toLowerCase();
    const langPrefix = langLower.split("-")[0];

    // 1. Exact match (e.g. te-IN)
    let matched = this.voices.find(
      (v) => v.lang && v.lang.toLowerCase() === langLower
    );

    // 2. Language prefix match (e.g. te or te_IN)
    if (!matched) {
      matched = this.voices.find(
        (v) => v.lang && v.lang.toLowerCase().replace("_", "-").startsWith(langPrefix)
      );
    }

    // 3. Fallback to default or first available voice
    if (matched) {
      return { voice: matched, isFallback: false };
    }

    const defaultVoice = this.voices.find((v) => v.default) || this.voices[0] || null;
    return { voice: defaultVoice, isFallback: true };
  }

  /**
   * Start speaking text associated with a unique caller ID.
   * If another utterance is active, it is immediately stopped.
   */
  speak({ id, text, preferredLang = null, rate = null }) {
    if (!this.isSupported) {
      console.warn("Web Speech API is not supported in this environment.");
      return;
    }

    if (!text || !text.trim()) return;

    // Stop any currently playing audio
    this.stop();

    if (rate !== null && Number.isFinite(rate)) {
      this.rate = rate;
    }

    // Clean markdown/HTML formatting for clean speech
    const cleanText = text
      .replace(/[*_#`~[\]()<>]/g, " ")
      .replace(/\s+/g, " ")
      .trim();

    if (!cleanText) return;

    // Detect actual script to avoid speaking English in a Telugu voice or vice-versa
    const detectedTag = detectScriptLanguage(cleanText);

    // If preferred language matches the detected script's general group, use it
    let targetLangTag = detectedTag;
    if (preferredLang) {
      const match = SUPPORTED_LANGUAGES.find(
        (l) => l.label.toLowerCase() === preferredLang.toLowerCase() ||
               l.code.toLowerCase() === preferredLang.toLowerCase()
      );
      if (match) {
        // If the text is English (Latin script), always speak English
        if (detectedTag.startsWith("en")) {
          targetLangTag = match.code === "en" ? (match.bcp47 || "en-IN") : "en-IN";
        } else {
          targetLangTag = match.bcp47;
        }
      }
    }

    const { voice, isFallback } = this._findBestVoice(targetLangTag);

    try {
      const utterance = new SpeechSynthesisUtterance(cleanText);
      utterance.rate = this.rate;
      utterance.pitch = 1.0;
      utterance.lang = targetLangTag;

      if (voice) {
        utterance.voice = voice;
      }

      this.activeId = id;
      this.isPlaying = true;
      this.isPaused = false;
      this.activeLanguage = targetLangTag;
      this.isFallbackVoice = isFallback;
      this.currentUtterance = utterance;

      utterance.onstart = () => {
        this.isPlaying = true;
        this.isPaused = false;
        this._notify();
      };

      utterance.onpause = () => {
        this.isPaused = true;
        this._notify();
      };

      utterance.onresume = () => {
        this.isPaused = false;
        this._notify();
      };

      utterance.onend = () => {
        if (this.activeId === id) {
          this.activeId = null;
          this.isPlaying = false;
          this.isPaused = false;
          this.currentUtterance = null;
          this._notify();
        }
      };

      utterance.onerror = (e) => {
        // Interrupted/canceled errors are expected on manual stop
        if (e.error !== "canceled" && e.error !== "interrupted") {
          console.warn("Speech synthesis notice:", e.error);
        }
        if (this.activeId === id) {
          this.activeId = null;
          this.isPlaying = false;
          this.isPaused = false;
          this.currentUtterance = null;
          this._notify();
        }
      };

      this._notify();
      window.speechSynthesis.speak(utterance);
    } catch (err) {
      console.error("SpeechSynthesis execution error:", err);
      this.stop();
    }
  }

  pause() {
    if (!this.isSupported || !this.isPlaying) return;
    try {
      window.speechSynthesis.pause();
      this.isPaused = true;
      this._notify();
    } catch (err) {
      console.error("Speech pause error:", err);
    }
  }

  resume() {
    if (!this.isSupported) return;
    try {
      window.speechSynthesis.resume();
      this.isPaused = false;
      this._notify();
    } catch (err) {
      console.error("Speech resume error:", err);
    }
  }

  stop() {
    if (!this.isSupported) return;
    try {
      window.speechSynthesis.cancel();
    } catch (err) {
      console.error("Speech cancel error:", err);
    } finally {
      this.activeId = null;
      this.isPlaying = false;
      this.isPaused = false;
      this.currentUtterance = null;
      this._notify();
    }
  }

  setRate(newRate) {
    if (!Number.isFinite(newRate)) return;
    this.rate = Math.max(0.5, Math.min(2.0, newRate));
    this._notify();
  }
}

export const speechService = new SpeechService();
