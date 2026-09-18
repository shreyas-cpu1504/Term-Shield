import React, { useEffect, useState } from "react";
import { FileText, ShieldAlert, Lightbulb } from "lucide-react";
import TermShieldLogo from "./TermShieldLogo";
import "./SplashScreen.css";

const TOTAL_DURATION_MS = 3000;
const FADE_OUT_START_MS = 2550;

export default function SplashScreen({ onComplete }) {
  const [progress, setProgress] = useState(0);
  const [isExiting, setIsExiting] = useState(false);

  useEffect(() => {
    const startTime = performance.now();
    let animationFrameId;

    const updateProgress = (now) => {
      const elapsed = now - startTime;
      const calculatedProgress = Math.min(100, (elapsed / TOTAL_DURATION_MS) * 100);
      setProgress(calculatedProgress);

      if (elapsed >= FADE_OUT_START_MS && !isExiting) {
        setIsExiting(true);
      }

      if (elapsed < TOTAL_DURATION_MS) {
        animationFrameId = requestAnimationFrame(updateProgress);
      }
    };

    animationFrameId = requestAnimationFrame(updateProgress);

    const completionTimer = setTimeout(() => {
      if (onComplete) {
        onComplete();
      }
    }, TOTAL_DURATION_MS);

    return () => {
      if (animationFrameId) {
        cancelAnimationFrame(animationFrameId);
      }
      clearTimeout(completionTimer);
    };
  }, [onComplete]);

  return (
    <div
      className={`ts-splash-overlay ${isExiting ? "ts-splash-exit" : ""}`}
      role="region"
      aria-label="Term Shield Loading Screen"
    >
      {/* Ambient background light waves & energy glow */}
      <div className="ts-splash-ambient" aria-hidden="true">
        <div className="ts-splash-light-wave-left" />
        <div className="ts-splash-light-wave-right" />
      </div>

      {/* Top Header Row */}
      <header className="ts-splash-top-bar">
        <div className="ts-splash-top-left">
          SECURE &nbsp;|&nbsp; SMART &nbsp;|&nbsp; TRANSPARENT
        </div>
        <div className="ts-splash-top-right">
          Your Terms Our Clarity
        </div>
      </header>

      {/* Center Branding & Progress */}
      <main className="ts-splash-center">
        {/* Luminous Logo Treatment */}
        <div className="ts-splash-logo-container">
          <TermShieldLogo size={96} glow={true} showAura={true} showOrbitalRing={true} />
        </div>

        {/* Wordmark: Term (white) Shield (gradient) */}
        <h1 className="ts-splash-wordmark">
          <span className="ts-splash-term">Term</span>
          <span className="ts-splash-shield">Shield</span>
        </h1>

        {/* Tagline */}
        <div className="ts-splash-tagline" aria-label="Understand today. Agree tomorrow.">
          <div>UNDERSTAND TODAY.</div>
          <div>AGREE TOMORROW.</div>
        </div>

        {/* Progress Bar & Percentage */}
        <div className="ts-splash-progress-row">
          <div
            className="ts-splash-progress-track"
            role="progressbar"
            aria-valuenow={Math.round(progress)}
            aria-valuemin="0"
            aria-valuemax="100"
          >
            <div
              className="ts-splash-progress-fill"
              style={{ width: `${progress}%` }}
            />
          </div>
          <span className="ts-splash-percent-text">{Math.round(progress)}%</span>
        </div>
      </main>

      {/* Bottom Capabilities & Micro Footer */}
      <footer className="ts-splash-bottom-wrap">
        <div className="ts-splash-capabilities" aria-label="Key Features">
          {/* Feature 1 */}
          <div className="ts-splash-cap-item">
            <div className="ts-splash-cap-icon-box purple">
              <FileText size={18} strokeWidth={2.2} />
            </div>
            <span className="ts-splash-cap-label">SIMPLIFY CONTRACTS</span>
          </div>

          {/* Feature 2 */}
          <div className="ts-splash-cap-item">
            <div className="ts-splash-cap-icon-box blue">
              <ShieldAlert size={18} strokeWidth={2.2} />
            </div>
            <span className="ts-splash-cap-label">SPOT RISKS</span>
          </div>

          {/* Feature 3 */}
          <div className="ts-splash-cap-item">
            <div className="ts-splash-cap-icon-box cyan">
              <Lightbulb size={18} strokeWidth={2.2} />
            </div>
            <span className="ts-splash-cap-label">GET CLEAR ANSWERS</span>
          </div>
        </div>

        <div className="ts-splash-micro-footer">
          POWERED BY AI &nbsp;&nbsp; FOR A SAFER TOMORROW
        </div>
      </footer>
    </div>
  );
}
