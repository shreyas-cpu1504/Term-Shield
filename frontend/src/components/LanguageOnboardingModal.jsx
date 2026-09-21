import React, { useState, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  Shield,
  Check,
  ArrowRight,
  ArrowLeft,
  Volume2,
  BookOpen,
  Headphones,
  Sliders,
  Sparkles,
  FileCheck2,
  AlertTriangle,
  CreditCard,
  CheckCircle2,
  Globe2,
  FileText,
  HelpCircle,
  Zap,
} from "lucide-react";
import TermShieldPulse from "./TermShieldPulse";
import {
  SUPPORTED_LANGUAGES,
  INFO_PREFERENCES,
  EXPLANATION_STYLES,
  PRIMARY_USES,
  DEFAULT_LANGUAGE_PREFERENCES,
  getLanguagePreferences,
  saveLanguagePreferences,
} from "../services/languagePreferences";

export default function LanguageOnboardingModal({ isOpen, onClose, onComplete, userId }) {
  const [currentStep, setCurrentStep] = useState(1);
  const [selectedLanguage, setSelectedLanguage] = useState("English");
  const [selectedInfoPref, setSelectedInfoPref] = useState("Read + Listen");
  const [selectedStyle, setSelectedStyle] = useState("Standard");
  const [selectedPrimaryUse, setSelectedPrimaryUse] = useState("All of these");

  useEffect(() => {
    if (isOpen) {
      setCurrentStep(1);
      const current = getLanguagePreferences(userId);
      if (current) {
        setSelectedLanguage(current.language || "English");
        setSelectedInfoPref(current.infoPreference || "Read + Listen");
        setSelectedStyle(current.explanationStyle || "Standard");
        setSelectedPrimaryUse(current.primaryUse || "All of these");
      }
    }
  }, [isOpen, userId]);

  if (!isOpen) return null;

  const handleNext = () => {
    if (currentStep < 4) {
      setCurrentStep((prev) => prev + 1);
    } else {
      handleFinish();
    }
  };

  const handleBack = () => {
    if (currentStep > 1) {
      setCurrentStep((prev) => prev - 1);
    }
  };

  const handleSkip = () => {
    const saved = saveLanguagePreferences({
      ...DEFAULT_LANGUAGE_PREFERENCES,
      onboardingCompleted: true,
    }, userId);
    onComplete?.(saved);
    onClose?.();
  };

  const handleFinish = () => {
    const preferences = {
      language: selectedLanguage,
      infoPreference: selectedInfoPref,
      explanationStyle: selectedStyle,
      primaryUse: selectedPrimaryUse,
      onboardingCompleted: true,
    };
    const saved = saveLanguagePreferences(preferences, userId);
    onComplete?.(saved);
    onClose?.();
  };

  const stepLabels = [
    { num: "01", name: "Language" },
    { num: "02", name: "Delivery" },
    { num: "03", name: "Explanation" },
    { num: "04", name: "Primary Use" },
  ];

  return (
    <div
      className="onboarding-viewport-shell"
      role="dialog"
      aria-modal="true"
      aria-labelledby="onboarding-step-heading"
    >
      {/* ========================================================
          LEFT PANEL (~40%): Premium Dark Gradient & Branding
      ======================================================== */}
      <aside className="onboarding-left-panel">
        {/* Subtle Background Particle Dots */}
        <div className="onboarding-ambient-glow" aria-hidden="true" />
        <div className="onboarding-particles-canvas" aria-hidden="true">
          {[...Array(6)].map((_, i) => (
            <motion.span
              key={i}
              className={`ambient-particle particle-${i}`}
              animate={{
                y: [0, -18, 0],
                opacity: [0.25, 0.6, 0.25],
              }}
              transition={{
                repeat: Infinity,
                duration: 4 + i * 1.2,
                ease: "easeInOut",
              }}
            />
          ))}
        </div>

        {/* Top Brand Header */}
        <div className="onboarding-left-top">
          <div className="onboarding-brand-pill">
            <div className="brand-logo-hex">
              <Shield size={18} className="brand-shield-svg" />
            </div>
            <div className="brand-title-wrap">
              <span className="brand-primary-name">Term Shield</span>
              <span className="brand-sub-badge">Contract Intelligence</span>
            </div>
          </div>
        </div>

        {/* Center Hero Identity Content */}
        <div className="onboarding-left-hero">
          <motion.div
            className="hero-pulse-container"
            initial={{ opacity: 0, scale: 0.9 }}
            animate={{ opacity: 1, scale: 1 }}
            transition={{ duration: 0.8, ease: "easeOut" }}
          >
            <TermShieldPulse size="hero" />
          </motion.div>

          <motion.h1
            className="hero-main-tagline"
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.2, duration: 0.6 }}
          >
            Understand Every Term.
            <br />
            <span className="gradient-highlight">Protect Every Decision.</span>
          </motion.h1>

          <motion.p
            className="hero-supporting-text"
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.35, duration: 0.6 }}
          >
            AI-powered contract intelligence designed to make complex legal
            agreements transparent, accessible, and actionable in your language.
          </motion.p>
        </div>

        {/* Bottom Reassurance Anchor */}
        <div className="onboarding-left-bottom">
          <span className="bottom-confidence-quote">
            Your contracts. Your understanding. Your control.
          </span>
        </div>
      </aside>

      {/* ========================================================
          RIGHT PANEL (~60%): Clean Interactive Wizard
      ======================================================== */}
      <main className="onboarding-right-panel">
        <div className="onboarding-right-content">
          {/* Top Progress Navigation Bar */}
          <div className="onboarding-top-status-bar">
            <div className="progress-counter-group">
              <span className="current-step-display">
                0{currentStep} <span className="step-total-divider">/ 04</span>
              </span>
              <span className="step-category-name">
                {stepLabels[currentStep - 1].name}
              </span>
            </div>

            <div className="progress-track-wrapper">
              <div className="progress-track-bg">
                <motion.div
                  className="progress-track-fill"
                  initial={false}
                  animate={{ width: `${(currentStep / 4) * 100}%` }}
                  transition={{ duration: 0.35, ease: "easeInOut" }}
                />
              </div>
            </div>

            <button
              type="button"
              className="onboarding-skip-action-btn"
              onClick={handleSkip}
              title="Skip setup and use default settings"
              aria-label="Skip onboarding setup for now"
            >
              Skip for now
            </button>
          </div>

          {/* Interactive Steps via Framer Motion Animated Transitions */}
          <div className="onboarding-step-body-container">
            <AnimatePresence mode="wait">
              {/* STEP 1: LANGUAGE SELECTION */}
              {currentStep === 1 && (
                <motion.div
                  key="step-1"
                  className="onboarding-step-view"
                  initial={{ opacity: 0, x: 20 }}
                  animate={{ opacity: 1, x: 0 }}
                  exit={{ opacity: 0, x: -20 }}
                  transition={{ duration: 0.28, ease: "easeInOut" }}
                >
                  <div className="onboarding-step-header">
                    <span className="onboarding-step-eyebrow">
                      PERSONALIZE YOUR EXPERIENCE
                    </span>
                    <h2 id="onboarding-step-heading" className="step-main-title">
                      Choose Your Primary Language
                    </h2>
                    <p className="step-desc-text">
                      Term Shield explains legal terms and answers contract
                      questions in your chosen language. Your uploaded contracts
                      retain their original text.
                    </p>
                  </div>

                  <div
                    className="language-selector-grid"
                    role="radiogroup"
                    aria-label="Choose your preferred language"
                  >
                    {SUPPORTED_LANGUAGES.map((lang) => {
                      const isSelected = selectedLanguage === lang.label;
                      return (
                        <motion.button
                          key={lang.code}
                          type="button"
                          role="radio"
                          aria-checked={isSelected}
                          className={`lang-option-card ${isSelected ? "selected" : ""}`}
                          onClick={() => setSelectedLanguage(lang.label)}
                          whileHover={{ scale: 1.015, y: -2 }}
                          whileTap={{ scale: 0.985 }}
                          transition={{ duration: 0.15 }}
                        >
                          <div className="lang-option-indicator">
                            <span className={`custom-radio-dot ${isSelected ? "checked" : ""}`}>
                              {isSelected && <Check size={12} strokeWidth={3} />}
                            </span>
                          </div>

                          <div className="lang-option-typography">
                            <span className="lang-native-script">
                              {lang.native}
                            </span>
                            <span className="lang-english-label">
                              {lang.label}
                            </span>
                          </div>

                          <div className="lang-option-icon-slot">
                            <Globe2 size={16} className="lang-globe-icon" />
                          </div>
                        </motion.button>
                      );
                    })}
                  </div>
                </motion.div>
              )}

              {/* STEP 2: INFORMATION DELIVERY PREFERENCE */}
              {currentStep === 2 && (
                <motion.div
                  key="step-2"
                  className="onboarding-step-view"
                  initial={{ opacity: 0, x: 20 }}
                  animate={{ opacity: 1, x: 0 }}
                  exit={{ opacity: 0, x: -20 }}
                  transition={{ duration: 0.28, ease: "easeInOut" }}
                >
                  <div className="onboarding-step-header">
                    <span className="onboarding-step-eyebrow">
                      ACCESSIBILITY &amp; COMFORT
                    </span>
                    <h2 id="onboarding-step-heading" className="step-main-title">
                      How would you like to receive information?
                    </h2>
                    <p className="step-desc-text">
                      Select your preferred mode for reading contract guidance,
                      obligation summaries, and answers.
                    </p>
                  </div>

                  <div
                    className="delivery-cards-stack"
                    role="radiogroup"
                    aria-label="Information delivery mode"
                  >
                    {INFO_PREFERENCES.map((pref) => {
                      const isSelected = selectedInfoPref === pref.id;
                      let IconComponent = BookOpen;
                      if (pref.id === "Listen") IconComponent = Headphones;
                      if (pref.id === "Read + Listen") IconComponent = Volume2;

                      return (
                        <motion.button
                          key={pref.id}
                          type="button"
                          role="radio"
                          aria-checked={isSelected}
                          className={`delivery-choice-card ${isSelected ? "selected" : ""}`}
                          onClick={() => setSelectedInfoPref(pref.id)}
                          whileHover={{ scale: 1.01, y: -2 }}
                          whileTap={{ scale: 0.99 }}
                          transition={{ duration: 0.15 }}
                        >
                          <div className="delivery-card-icon-hex">
                            <IconComponent size={22} className="delivery-icon" />
                          </div>

                          <div className="delivery-card-details">
                            <div className="delivery-card-title-row">
                              <strong className="delivery-title">
                                {pref.label}
                              </strong>
                              {pref.id === "Read + Listen" && (
                                <span className="recommended-badge">
                                  <Sparkles size={11} />
                                  <span>Recommended</span>
                                </span>
                              )}
                            </div>
                            <p className="delivery-desc">{pref.description}</p>
                          </div>

                          <div className="delivery-card-check">
                            <span className={`choice-check-circle ${isSelected ? "checked" : ""}`}>
                              {isSelected && <Check size={14} strokeWidth={3} />}
                            </span>
                          </div>
                        </motion.button>
                      );
                    })}
                  </div>
                </motion.div>
              )}

              {/* STEP 3: EXPLANATION STYLE & INTERACTIVE PREVIEW */}
              {currentStep === 3 && (
                <motion.div
                  key="step-3"
                  className="onboarding-step-view"
                  initial={{ opacity: 0, x: 20 }}
                  animate={{ opacity: 1, x: 0 }}
                  exit={{ opacity: 0, x: -20 }}
                  transition={{ duration: 0.28, ease: "easeInOut" }}
                >
                  <div className="onboarding-step-header">
                    <span className="onboarding-step-eyebrow">
                      COMPREHENSION PREFERENCE
                    </span>
                    <h2 id="onboarding-step-heading" className="step-main-title">
                      How should Term Shield explain terms?
                    </h2>
                    <p className="step-desc-text">
                      Choose between standard contractual language or clear,
                      plain-language translations designed for everyday clarity.
                    </p>
                  </div>

                  <div
                    className="style-cards-stack"
                    role="radiogroup"
                    aria-label="Explanation style"
                  >
                    {EXPLANATION_STYLES.map((style) => {
                      const isSelected = selectedStyle === style.id;
                      const IconComponent = style.id === "Standard" ? Sliders : Zap;

                      return (
                        <motion.button
                          key={style.id}
                          type="button"
                          role="radio"
                          aria-checked={isSelected}
                          className={`style-choice-card ${isSelected ? "selected" : ""}`}
                          onClick={() => setSelectedStyle(style.id)}
                          whileHover={{ scale: 1.01, y: -2 }}
                          whileTap={{ scale: 0.99 }}
                          transition={{ duration: 0.15 }}
                        >
                          <div className="style-card-icon-hex">
                            <IconComponent size={20} className="style-icon" />
                          </div>

                          <div className="style-card-details">
                            <strong className="style-title">{style.label}</strong>
                            <p className="style-desc">{style.description}</p>
                          </div>

                          <div className="style-card-check">
                            <span className={`choice-check-circle ${isSelected ? "checked" : ""}`}>
                              {isSelected && <Check size={14} strokeWidth={3} />}
                            </span>
                          </div>
                        </motion.button>
                      );
                    })}
                  </div>

                  {/* Polished Interactive Live Preview Box */}
                  <div className="live-preview-card">
                    <div className="preview-top-bar">
                      <div className="preview-indicator-chip">
                        <span className="preview-pulse-dot" />
                        <span>LIVE PREVIEW</span>
                      </div>
                      <span className="preview-mode-tag">
                        Current Mode: <strong>{selectedStyle}</strong>
                      </span>
                    </div>

                    <div className="preview-question-row">
                      <HelpCircle size={15} className="preview-q-icon" />
                      <strong>Who is responsible if something goes wrong?</strong>
                    </div>

                    <div className="preview-answer-container">
                      <AnimatePresence mode="wait">
                        {selectedStyle === "Simple" ? (
                          <motion.div
                            key="simple-preview"
                            className="preview-answer-text simple"
                            initial={{ opacity: 0, y: 6 }}
                            animate={{ opacity: 1, y: 0 }}
                            exit={{ opacity: 0, y: -6 }}
                            transition={{ duration: 0.2 }}
                          >
                            <p>
                              If something goes wrong, neither side has to pay more
                              than what was paid under this contract in the past 12
                              months. However, there is no dollar cap if someone
                              leaks private or confidential information.
                            </p>
                            <span className="preview-annotation-badge">
                              Plain Language Mode: Translates legalese into everyday terms
                            </span>
                          </motion.div>
                        ) : (
                          <motion.div
                            key="standard-preview"
                            className="preview-answer-text standard"
                            initial={{ opacity: 0, y: 6 }}
                            animate={{ opacity: 1, y: 0 }}
                            exit={{ opacity: 0, y: -6 }}
                            transition={{ duration: 0.2 }}
                          >
                            <p>
                              Under Section 14.2 (Limitation of Liability), each
                              party's aggregate indemnification obligation for
                              direct damages is capped at fees paid in the
                              preceding 12 months, excluding breaches of
                              confidentiality covenants.
                            </p>
                            <span className="preview-annotation-badge">
                              Standard Legal Mode: Preserves formal contractual phrasing
                            </span>
                          </motion.div>
                        )}
                      </AnimatePresence>
                    </div>
                  </div>
                </motion.div>
              )}

              {/* STEP 4: PRIMARY USE & FINAL REVIEW */}
              {currentStep === 4 && (
                <motion.div
                  key="step-4"
                  className="onboarding-step-view"
                  initial={{ opacity: 0, x: 20 }}
                  animate={{ opacity: 1, x: 0 }}
                  exit={{ opacity: 0, x: -20 }}
                  transition={{ duration: 0.28, ease: "easeInOut" }}
                >
                  <div className="onboarding-step-header">
                    <span className="onboarding-step-eyebrow">
                      WORKSPACE SETUP
                    </span>
                    <h2 id="onboarding-step-heading" className="step-main-title">
                      How will you mainly use Term Shield?
                    </h2>
                    <p className="step-desc-text">
                      Help us personalize your default workspace highlights. You
                      can change any preference at any time in Settings.
                    </p>
                  </div>

                  <div
                    className="use-case-cards-stack"
                    role="radiogroup"
                    aria-label="Primary usage focus"
                  >
                    {PRIMARY_USES.map((use) => {
                      const isSelected = selectedPrimaryUse === use;
                      let UseIcon = FileText;
                      if (use.includes("risks")) UseIcon = AlertTriangle;
                      if (use.includes("payments")) UseIcon = CreditCard;
                      if (use.includes("responsibilities")) UseIcon = Shield;
                      if (use.includes("All")) UseIcon = Sparkles;

                      return (
                        <motion.button
                          key={use}
                          type="button"
                          role="radio"
                          aria-checked={isSelected}
                          className={`use-choice-card ${isSelected ? "selected" : ""}`}
                          onClick={() => setSelectedPrimaryUse(use)}
                          whileHover={{ scale: 1.01, y: -1 }}
                          whileTap={{ scale: 0.99 }}
                          transition={{ duration: 0.15 }}
                        >
                          <div className="use-card-icon-slot">
                            <UseIcon size={17} className="use-icon" />
                          </div>

                          <div className="use-card-label-wrap">
                            <strong className="use-card-title">{use}</strong>
                          </div>

                          <div className="use-card-check">
                            <span className={`choice-check-circle sm ${isSelected ? "checked" : ""}`}>
                              {isSelected && <Check size={12} strokeWidth={3} />}
                            </span>
                          </div>
                        </motion.button>
                      );
                    })}
                  </div>

                  {/* Summary Confirmation Badge */}
                  <div className="onboarding-review-summary-box">
                    <div className="review-summary-header">
                      <span>CONFIGURATION SUMMARY</span>
                    </div>
                    <div className="review-summary-grid">
                      <div className="summary-pill">
                        <span className="summary-key">Language</span>
                        <strong className="summary-val">{selectedLanguage}</strong>
                      </div>
                      <div className="summary-pill">
                        <span className="summary-key">Delivery</span>
                        <strong className="summary-val">{selectedInfoPref}</strong>
                      </div>
                      <div className="summary-pill">
                        <span className="summary-key">Style</span>
                        <strong className="summary-val">{selectedStyle}</strong>
                      </div>
                    </div>
                  </div>
                </motion.div>
              )}
            </AnimatePresence>
          </div>

          {/* Bottom Actions Bar */}
          <div className="onboarding-actions-footer">
            <div className="footer-left-col">
              {currentStep > 1 && (
                <motion.button
                  type="button"
                  className="onboarding-nav-btn secondary-back-btn"
                  onClick={handleBack}
                  whileHover={{ scale: 1.02 }}
                  whileTap={{ scale: 0.98 }}
                  aria-label="Return to previous onboarding step"
                >
                  <ArrowLeft size={16} />
                  <span>Back</span>
                </motion.button>
              )}
            </div>

            <div className="footer-right-col">
              {currentStep < 4 ? (
                <motion.button
                  type="button"
                  className="onboarding-nav-btn primary-continue-btn"
                  onClick={handleNext}
                  whileHover={{ scale: 1.02 }}
                  whileTap={{ scale: 0.98 }}
                >
                  <span>Continue</span>
                  <ArrowRight size={16} />
                </motion.button>
              ) : (
                <motion.button
                  type="button"
                  className="onboarding-nav-btn primary-continue-btn finish-btn"
                  onClick={handleFinish}
                  whileHover={{ scale: 1.02 }}
                  whileTap={{ scale: 0.98 }}
                >
                  <span>Continue to Term Shield</span>
                  <ArrowRight size={16} />
                </motion.button>
              )}
            </div>
          </div>
        </div>
      </main>
    </div>
  );
}
