import React, { useState, useEffect, useRef } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  Volume2,
  Pause,
  Play,
  Square,
  ChevronDown,
  Info,
  Check,
} from "lucide-react";
import { speechService } from "../services/speechService";
import { getLanguagePreferences } from "../services/languagePreferences";

const SPEED_OPTIONS = [
  { value: 0.75, label: "0.75×" },
  { value: 1.0, label: "1.0×" },
  { value: 1.25, label: "1.25×" },
  { value: 1.5, label: "1.5×" },
];

export default function ListenButton({
  text,
  id: customId,
  label = "Listen",
  size = "md",
  className = "",
  preferredLanguage = null,
}) {
  const [speechState, setSpeechState] = useState(() => speechService.getState());
  const [showSpeedMenu, setShowSpeedMenu] = useState(false);
  const [showFallbackNotice, setShowFallbackNotice] = useState(false);
  const internalIdRef = useRef(
    customId || `listen-btn-${Math.random().toString(36).substring(2, 9)}`
  );
  const containerRef = useRef(null);

  useEffect(() => {
    const unsubscribe = speechService.subscribe((state) => {
      setSpeechState(state);
    });
    return () => unsubscribe();
  }, []);

  // Close speed popover when clicking outside
  useEffect(() => {
    if (!showSpeedMenu) return;
    const handleClickOutside = (e) => {
      if (containerRef.current && !containerRef.current.contains(e.target)) {
        setShowSpeedMenu(false);
      }
    };
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, [showSpeedMenu]);

  const buttonId = internalIdRef.current;
  const isThisActive = speechState.activeId === buttonId;
  const isPlaying = isThisActive && speechState.isPlaying && !speechState.isPaused;
  const isPaused = isThisActive && speechState.isPaused;

  const currentPreferences = getLanguagePreferences();
  const effectiveLanguage = preferredLanguage || currentPreferences.language;

  const handlePlay = (e) => {
    e?.stopPropagation();
    if (!text) return;

    if (isPaused) {
      speechService.resume();
    } else {
      speechService.speak({
        id: buttonId,
        text,
        preferredLang: effectiveLanguage,
        rate: speechState.rate,
      });

      // If voice fell back, show subtle non-blocking notice
      setTimeout(() => {
        const state = speechService.getState();
        if (state.activeId === buttonId && state.isFallbackVoice) {
          setShowFallbackNotice(true);
          setTimeout(() => setShowFallbackNotice(false), 4500);
        }
      }, 250);
    }
  };

  const handlePause = (e) => {
    e?.stopPropagation();
    speechService.pause();
  };

  const handleStop = (e) => {
    e?.stopPropagation();
    speechService.stop();
  };

  const handleSpeedSelect = (rateVal, e) => {
    e?.stopPropagation();
    speechService.setRate(rateVal);
    setShowSpeedMenu(false);
  };

  if (!speechState.isSupported || !text || !text.trim()) {
    return null;
  }

  const currentRateLabel =
    SPEED_OPTIONS.find((opt) => opt.value === speechState.rate)?.label ||
    `${speechState.rate}×`;

  return (
    <div
      className={`ts-listen-player-container ${size} ${className}`}
      ref={containerRef}
      role="region"
      aria-label="Text-to-speech player"
    >
      <div className="ts-listen-controls-bar">
        {!isThisActive || (!isPlaying && !isPaused) ? (
          /* IDLE STATE: Sleek audio launch pill */
          <motion.button
            type="button"
            className={`ts-listen-launch-btn ${size}`}
            onClick={handlePlay}
            whileHover={{ scale: 1.02 }}
            whileTap={{ scale: 0.98 }}
            title={`Listen in ${effectiveLanguage}`}
            aria-label={`Listen to this explanation in ${effectiveLanguage}`}
          >
            <span className="launch-icon-wrap">
              <Volume2 size={size === "sm" ? 13 : 15} />
            </span>
            <span className="launch-label">{label}</span>
          </motion.button>
        ) : (
          /* ACTIVE PLAYING / PAUSED STATE: Polished Audio Toolbar */
          <div className={`ts-listen-active-toolbar ${size}`} aria-live="polite">
            {/* Play/Pause Button */}
            {isPlaying ? (
              <button
                type="button"
                className="ts-toolbar-btn pause-btn"
                onClick={handlePause}
                title="Pause speech"
                aria-label="Pause speech"
              >
                <Pause size={13} />
                <span>Pause</span>
              </button>
            ) : (
              <button
                type="button"
                className="ts-toolbar-btn resume-btn"
                onClick={handlePlay}
                title="Resume speech"
                aria-label="Resume speech"
              >
                <Play size={13} />
                <span>Resume</span>
              </button>
            )}

            {/* Stop Button */}
            <button
              type="button"
              className="ts-toolbar-btn stop-btn"
              onClick={handleStop}
              title="Stop playback"
              aria-label="Stop playback"
            >
              <Square size={11} />
              <span>Stop</span>
            </button>

            <span className="ts-toolbar-divider" />

            {/* Speed Popover Trigger */}
            <div className="ts-speed-popover-anchor">
              <button
                type="button"
                className="ts-speed-pill-btn"
                onClick={(e) => {
                  e.stopPropagation();
                  setShowSpeedMenu((prev) => !prev);
                }}
                title="Select playback speed"
                aria-label={`Playback speed: ${currentRateLabel}`}
                aria-expanded={showSpeedMenu}
              >
                <span>{currentRateLabel}</span>
                <ChevronDown size={11} className={`chevron-icon ${showSpeedMenu ? "rotated" : ""}`} />
              </button>

              {/* Speed Menu Popover */}
              <AnimatePresence>
                {showSpeedMenu && (
                  <motion.div
                    className="ts-speed-menu-popover"
                    initial={{ opacity: 0, scale: 0.95, y: 4 }}
                    animate={{ opacity: 1, scale: 1, y: 0 }}
                    exit={{ opacity: 0, scale: 0.95, y: 4 }}
                    transition={{ duration: 0.15 }}
                    role="menu"
                  >
                    <div className="speed-menu-header">Speech Speed</div>
                    {SPEED_OPTIONS.map((opt) => {
                      const isSelected = speechState.rate === opt.value;
                      return (
                        <button
                          key={opt.value}
                          type="button"
                          className={`speed-menu-item ${isSelected ? "selected" : ""}`}
                          onClick={(e) => handleSpeedSelect(opt.value, e)}
                          role="menuitem"
                        >
                          <span>{opt.label}</span>
                          {isSelected && <Check size={12} strokeWidth={2.5} />}
                        </button>
                      );
                    })}
                  </motion.div>
                )}
              </AnimatePresence>
            </div>

            {/* Animated Equalizer Waveform */}
            {isPlaying && (
              <div className="ts-audio-equalizer" aria-hidden="true">
                <span className="eq-bar bar-1" />
                <span className="eq-bar bar-2" />
                <span className="eq-bar bar-3" />
                <span className="eq-bar bar-4" />
              </div>
            )}
          </div>
        )}
      </div>

      {/* Non-blocking Subtle Fallback Notice */}
      <AnimatePresence>
        {showFallbackNotice && isThisActive && (
          <motion.div
            className="ts-voice-fallback-pill"
            initial={{ opacity: 0, y: -4 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -4 }}
            transition={{ duration: 0.2 }}
            role="status"
          >
            <Info size={12} className="info-icon" />
            <span>
              Device native {effectiveLanguage} voice not installed; using standard browser voice.
            </span>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
