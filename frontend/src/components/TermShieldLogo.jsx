import React from "react";

export default function TermShieldLogo({
  size = 54,
  glow = true,
  className = "",
  showAura = false,
  showOrbitalRing = true,
}) {
  const width = size;
  const height = size;

  return (
    <div
      className={`term-shield-logo-wrap ${className}`}
      style={{
        position: "relative",
        width,
        height,
        display: "inline-grid",
        placeItems: "center",
        flexShrink: 0,
      }}
      aria-hidden="true"
    >
      {/* Ambient background soft glow aura */}
      {showAura && (
        <div
          style={{
            position: "absolute",
            inset: "-25%",
            borderRadius: "50%",
            background:
              "radial-gradient(circle, rgba(56, 189, 248, 0.35) 0%, rgba(168, 85, 247, 0.28) 45%, transparent 70%)",
            filter: "blur(24px)",
            pointerEvents: "none",
            zIndex: 0,
          }}
        />
      )}

      <svg
        width={width}
        height={height}
        viewBox="0 0 120 120"
        fill="none"
        xmlns="http://www.w3.org/2000/svg"
        style={{
          position: "relative",
          zIndex: 1,
          filter: glow
            ? "drop-shadow(0 6px 18px rgba(56, 189, 248, 0.42)) drop-shadow(0 0 24px rgba(168, 85, 247, 0.35))"
            : "none",
          overflow: "visible",
        }}
      >
        <defs>
          {/* Outer Shield Neon Rim Gradient (Cyan -> Electric Blue -> Violet -> Magenta) */}
          <linearGradient id="tsRimGrad" x1="15" y1="15" x2="105" y2="105" gradientUnits="userSpaceOnUse">
            <stop offset="0%" stopColor="#38bdf8" />
            <stop offset="35%" stopColor="#2563eb" />
            <stop offset="70%" stopColor="#8b5cf6" />
            <stop offset="100%" stopColor="#e879f9" />
          </linearGradient>

          {/* Shield Glass Body Gradient */}
          <radialGradient id="tsGlassBody" cx="50%" cy="40%" r="60%">
            <stop offset="0%" stopColor="#1e1b4b" stopOpacity="0.85" />
            <stop offset="60%" stopColor="#0f172a" stopOpacity="0.94" />
            <stop offset="100%" stopColor="#020617" stopOpacity="0.98" />
          </radialGradient>

          {/* Shield Interior Highlight */}
          <linearGradient id="tsShieldGloss" x1="30" y1="20" x2="70" y2="80" gradientUnits="userSpaceOnUse">
            <stop offset="0%" stopColor="#60a5fa" stopOpacity="0.5" />
            <stop offset="40%" stopColor="#a855f7" stopOpacity="0.2" />
            <stop offset="100%" stopColor="#ffffff" stopOpacity="0" />
          </linearGradient>

          {/* Document Body Gradient */}
          <linearGradient id="tsDocGrad" x1="42" y1="36" x2="78" y2="84" gradientUnits="userSpaceOnUse">
            <stop offset="0%" stopColor="#c084fc" />
            <stop offset="50%" stopColor="#818cf8" />
            <stop offset="100%" stopColor="#4f46e5" />
          </linearGradient>

          {/* Document Folded Corner Gradient */}
          <linearGradient id="tsDocFold" x1="68" y1="36" x2="78" y2="46" gradientUnits="userSpaceOnUse">
            <stop offset="0%" stopColor="#ffffff" />
            <stop offset="100%" stopColor="#c084fc" />
          </linearGradient>

          {/* Document Clauses Line Gradient */}
          <linearGradient id="tsLineGrad" x1="46" y1="58" x2="72" y2="58" gradientUnits="userSpaceOnUse">
            <stop offset="0%" stopColor="#ffffff" stopOpacity="0.95" />
            <stop offset="100%" stopColor="#e0e7ff" stopOpacity="0.8" />
          </linearGradient>

          {/* AI Spark Star Gradient */}
          <radialGradient id="tsSparkGlow" cx="50%" cy="50%" r="50%">
            <stop offset="0%" stopColor="#ffffff" />
            <stop offset="30%" stopColor="#67e8f9" />
            <stop offset="70%" stopColor="#3b82f6" stopOpacity="0.6" />
            <stop offset="100%" stopColor="#38bdf8" stopOpacity="0" />
          </radialGradient>

          {/* Orbital Light Wave Gradient */}
          <linearGradient id="tsOrbitGrad" x1="10" y1="60" x2="110" y2="60" gradientUnits="userSpaceOnUse">
            <stop offset="0%" stopColor="#38bdf8" stopOpacity="0.1" />
            <stop offset="25%" stopColor="#38bdf8" stopOpacity="0.85" />
            <stop offset="60%" stopColor="#a855f7" stopOpacity="0.9" />
            <stop offset="100%" stopColor="#ec4899" stopOpacity="0.1" />
          </linearGradient>
        </defs>

        {/* Back portion of the Orbital Ring */}
        {showOrbitalRing && (
          <ellipse
            cx="60"
            cy="62"
            rx="46"
            ry="18"
            transform="rotate(-20 60 62)"
            stroke="url(#tsOrbitGrad)"
            strokeWidth="2.2"
            strokeDasharray="95 30"
            strokeDashoffset="15"
            strokeOpacity="0.6"
          />
        )}

        {/* Outer Shield Neon Glow Base / Aura Path */}
        <path
          d="M 60 16 
             C 80 16, 96 22, 99 32 
             C 101 56, 93 84, 60 104 
             C 27 84, 19 56, 21 32 
             C 24 22, 40 16, 60 16 Z"
          fill="url(#tsGlassBody)"
          stroke="url(#tsRimGrad)"
          strokeWidth="4.5"
          strokeLinejoin="round"
        />

        {/* Inner Glass Sheen / Rim Accent */}
        <path
          d="M 60 21 
             C 77 21, 91 26, 94 34 
             C 96 54, 88 78, 60 96 
             C 32 78, 24 54, 26 34 
             C 29 26, 43 21, 60 21 Z"
          fill="none"
          stroke="url(#tsShieldGloss)"
          strokeWidth="1.75"
        />

        {/* Stylized Document Inside the Shield */}
        {/* Document Body with Folded Top-Right Corner */}
        <path
          d="M 44 40 
             L 66 40 
             L 76 50 
             L 76 80 
             C 76 83, 74 85, 71 85 
             L 44 85 
             C 41 85, 39 83, 39 80 
             L 39 45 
             C 39 42, 41 40, 44 40 Z"
          fill="url(#tsDocGrad)"
          filter="drop-shadow(0 4px 10px rgba(15, 23, 42, 0.55))"
        />

        {/* Document Folded Flap */}
        <path
          d="M 66 40 
             L 66 49 
             C 66 50, 67 50, 68 50 
             L 76 50 Z"
          fill="url(#tsDocFold)"
        />

        {/* Document Clause / Text Lines */}
        <line
          x1="46"
          y1="56"
          x2="68"
          y2="56"
          stroke="url(#tsLineGrad)"
          strokeWidth="2.5"
          strokeLinecap="round"
        />
        <line
          x1="46"
          y1="64"
          x2="68"
          y2="64"
          stroke="url(#tsLineGrad)"
          strokeWidth="2.5"
          strokeLinecap="round"
        />
        <line
          x1="46"
          y1="72"
          x2="59"
          y2="72"
          stroke="url(#tsLineGrad)"
          strokeWidth="2.5"
          strokeLinecap="round"
        />

        {/* Front portion of Orbital Ring (overlaps shield seamlessly) */}
        {showOrbitalRing && (
          <path
            d="M 17 64 
               C 22 75, 46 82, 72 79 
               C 92 76, 106 67, 104 58"
            stroke="url(#tsOrbitGrad)"
            strokeWidth="3.2"
            strokeLinecap="round"
            filter="drop-shadow(0 0 6px #38bdf8)"
          />
        )}

        {/* Radiant 4-Point AI Spark / Star on Document Right Shoulder */}
        {/* Soft Glow Core */}
        <circle cx="78" cy="46" r="12" fill="url(#tsSparkGlow)" />
        
        {/* Diamond 4-Point Spark */}
        <path
          d="M 78 35 
             Q 78 46, 89 46 
             Q 78 46, 78 57 
             Q 78 46, 67 46 
             Q 78 46, 78 35 Z"
          fill="#ffffff"
          filter="drop-shadow(0 0 5px #67e8f9)"
        />

        {/* Brilliant Center Dot */}
        <circle cx="78" cy="46" r="1.5" fill="#ffffff" />
      </svg>
    </div>
  );
}
