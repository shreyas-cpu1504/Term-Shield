/**
 * SpeechService - Centralized Multilingual Speech Coordinator for Term Shield.
 * Guarantees single-utterance playback across the application, manages
 * natural Indic/multilingual audio synthesis (Telugu, Hindi, Tamil, Kannada,
 * Malayalam, Bengali, Marathi, Gujarati, Urdu) as well as native Web Speech API,
 * voice matching, fallback, pause/resume/stop, speed control, and state notification.
 */

import { detectScriptLanguage, SUPPORTED_LANGUAGES } from "./languagePreferences";
import apiClient from "../api/client";

class SpeechService {
  constructor() {
    this.currentUtterance = null;
    this.currentAudio = null;
    this.currentAbortController = null;
    this.activeId = null;
    this.isPlaying = false;
    this.isPaused = false;
    this.rate = 1.0;
    this.activeLanguage = "en-IN";
    this.isFallbackVoice = false;
    this.listeners = new Set();
    this.voices = [];
    this.isSupported = typeof window !== "undefined";

    if (typeof window !== "undefined" && "speechSynthesis" in window) {
      this._loadVoices();
      if (window.speechSynthesis.onvoiceschanged !== undefined) {
        window.speechSynthesis.onvoiceschanged = () => this._loadVoices();
      }
    }
  }

  _loadVoices() {
    if (typeof window === "undefined" || !("speechSynthesis" in window)) return;
    this.voices = window.speechSynthesis.getVoices() || [];
  }

  /**
   * Subscribe a component to speech state changes.
   */
  subscribe(listener) {
    this.listeners.add(listener);
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
   * Find native browser voice if available.
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

    // 3. Name match for Indic languages (e.g. "Mohan - Telugu", "Google Telugu")
    if (!matched) {
      const matchLangObj = SUPPORTED_LANGUAGES.find(
        (l) => l.code.toLowerCase() === langPrefix || l.bcp47.toLowerCase() === langLower
      );
      if (matchLangObj) {
        const langName = matchLangObj.label.toLowerCase();
        matched = this.voices.find(
          (v) => v.name && v.name.toLowerCase().includes(langName)
        );
      }
    }

    if (matched) {
      return { voice: matched, isFallback: false };
    }

    const defaultVoice = this.voices.find((v) => v.default) || this.voices[0] || null;
    return { voice: defaultVoice, isFallback: true };
  }

  /**
   * Get backend base URL for TTS endpoint.
   */
  _getApiBaseUrl() {
    const fromClient = apiClient?.defaults?.baseURL;
    if (fromClient) {
      return fromClient.replace(/\/+$/, "");
    }
    return "http://127.0.0.1:8000/api/v1";
  }

  /**
   * Start speaking text associated with a unique caller ID.
   * Naturally handles multilingual, mixed-language (Indic + English legal terms),
   * pure Indic, and English text.
   */
  speak({ id, text, preferredLang = null, rate = null }) {
    if (!text || !text.trim()) return;

    // Stop any currently playing audio
    this.stop();

    if (rate !== null && Number.isFinite(rate)) {
      this.rate = rate;
    }

    // Clean markdown/HTML formatting for clean, natural speech
    const cleanText = text
      .replace(/[*_#`~[\]()<>{}|\\]/g, " ")
      .replace(/\s+/g, " ")
      .trim();

    if (!cleanText) return;

    // Detect actual script language taking into account preferred language and character counts
    const targetLangTag = detectScriptLanguage(cleanText, preferredLang);
    const hasIndicChars = /[\u0600-\u0D7F]/.test(cleanText);
    const isIndicOrMultilingual = hasIndicChars || !targetLangTag.startsWith("en");

    this.activeId = id;
    this.activeLanguage = targetLangTag;

    // For Indic or mixed-language text, use high-fidelity natural speech service
    // so that Indic words and embedded English legal terms are spoken completely.
    if (isIndicOrMultilingual) {
      this._speakWithAudioEngine({ id, cleanText, targetLangTag, preferredLang });
    } else {
      // Pure English text: use browser Web Speech API with fallback
      this._speakWithWebSpeech({ id, cleanText, targetLangTag, preferredLang });
    }
  }

  /**
   * High-fidelity audio stream engine for natural Indic & Multilingual text.
   */
  _speakWithAudioEngine({ id, cleanText, targetLangTag, preferredLang }) {
    try {
      const baseUrl = this._getApiBaseUrl();
      const langParam = targetLangTag.split("-")[0];
      const ttsUrl = `${baseUrl}/tts?text=${encodeURIComponent(cleanText)}&lang=${encodeURIComponent(langParam)}&preferred_lang=${encodeURIComponent(preferredLang || "")}`;

      const audio = new Audio(ttsUrl);
      audio.playbackRate = this.rate;

      this.currentAudio = audio;
      this.isFallbackVoice = false;

      audio.onplay = () => {
        if (this.activeId === id) {
          this.isPlaying = true;
          this.isPaused = false;
          this._notify();
        }
      };

      audio.onpause = () => {
        if (this.activeId === id && this.isPlaying) {
          this.isPaused = true;
          this._notify();
        }
      };

      audio.onended = () => {
        if (this.activeId === id) {
          this.stop();
        }
      };

      audio.onerror = () => {
        // Fallback to Web Speech API if backend audio endpoint could not be reached
        console.warn("Backend TTS stream unreachable; falling back to device speech engine.");
        if (this.activeId === id) {
          this.currentAudio = null;
          this._speakWithWebSpeech({ id, cleanText, targetLangTag, preferredLang });
        }
      };

      // Set initial playing state and trigger playback
      this.isPlaying = true;
      this.isPaused = false;
      this._notify();

      audio.play().catch((playErr) => {
        console.warn("Audio element play error:", playErr);
        if (this.activeId === id) {
          this._speakWithWebSpeech({ id, cleanText, targetLangTag, preferredLang });
        }
      });
    } catch (err) {
      console.error("Audio engine execution error:", err);
      this._speakWithWebSpeech({ id, cleanText, targetLangTag, preferredLang });
    }
  }

  /**
   * Web Speech API engine for pure English or offline fallback.
   */
  _speakWithWebSpeech({ id, cleanText, targetLangTag, preferredLang }) {
    if (typeof window === "undefined" || !("speechSynthesis" in window)) {
      console.warn("Speech synthesis is not supported on this browser.");
      this.stop();
      return;
    }

    const { voice, isFallback } = this._findBestVoice(targetLangTag);

    try {
      const utterance = new SpeechSynthesisUtterance(cleanText);
      utterance.rate = this.rate;
      utterance.pitch = 1.0;
      utterance.lang = targetLangTag;

      if (voice && !isFallback) {
        utterance.voice = voice;
      }

      this.activeId = id;
      this.isPlaying = true;
      this.isPaused = false;
      this.activeLanguage = targetLangTag;
      this.isFallbackVoice = isFallback;
      this.currentUtterance = utterance;

      utterance.onstart = () => {
        if (this.activeId === id) {
          this.isPlaying = true;
          this.isPaused = false;
          this._notify();
        }
      };

      utterance.onpause = () => {
        if (this.activeId === id) {
          this.isPaused = true;
          this._notify();
        }
      };

      utterance.onresume = () => {
        if (this.activeId === id) {
          this.isPaused = false;
          this._notify();
        }
      };

      utterance.onend = () => {
        if (this.activeId === id) {
          this.stop();
        }
      };

      utterance.onerror = (e) => {
        if (e.error !== "canceled" && e.error !== "interrupted") {
          console.warn("Speech synthesis notice:", e.error);
        }
        if (this.activeId === id) {
          this.stop();
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
    if (!this.isPlaying) return;

    if (this.currentAudio) {
      try {
        this.currentAudio.pause();
      } catch (err) {
        console.error("Audio pause error:", err);
      }
    } else if (typeof window !== "undefined" && "speechSynthesis" in window) {
      try {
        window.speechSynthesis.pause();
      } catch (err) {
        console.error("Speech pause error:", err);
      }
    }

    this.isPaused = true;
    this._notify();
  }

  resume() {
    if (this.currentAudio) {
      try {
        this.currentAudio.play();
        this.isPaused = false;
        this._notify();
      } catch (err) {
        console.error("Audio resume error:", err);
      }
    } else if (typeof window !== "undefined" && "speechSynthesis" in window) {
      try {
        window.speechSynthesis.resume();
        this.isPaused = false;
        this._notify();
      } catch (err) {
        console.error("Speech resume error:", err);
      }
    }
  }

  stop() {
    if (this.currentAudio) {
      try {
        this.currentAudio.pause();
        this.currentAudio.removeAttribute("src");
        this.currentAudio.load();
      } catch (err) {
        console.error("Audio stop error:", err);
      } finally {
        this.currentAudio = null;
      }
    }

    if (typeof window !== "undefined" && "speechSynthesis" in window) {
      try {
        window.speechSynthesis.cancel();
      } catch (err) {
        console.error("Speech cancel error:", err);
      } finally {
        this.currentUtterance = null;
      }
    }

    this.activeId = null;
    this.isPlaying = false;
    this.isPaused = false;
    this._notify();
  }

  setRate(newRate) {
    if (!Number.isFinite(newRate)) return;
    this.rate = Math.max(0.5, Math.min(2.0, newRate));

    if (this.currentAudio) {
      this.currentAudio.playbackRate = this.rate;
    }

    this._notify();
  }
}

export const speechService = new SpeechService();
