import React from "react";
import { motion } from "framer-motion";
import { Shield } from "lucide-react";

export default function TermShieldPulse({
  size = "md",
  label = null,
  className = "",
}) {
  const sizeMap = {
    sm: { container: 36, shield: 16, pulseRing: 46 },
    md: { container: 60, shield: 26, pulseRing: 78 },
    lg: { container: 92, shield: 40, pulseRing: 118 },
    hero: { container: 124, shield: 54, pulseRing: 160 },
  };

  const currentSize = sizeMap[size] || sizeMap.md;

  return (
    <div
      className={`term-shield-pulse-wrapper ${size} ${className}`}
      style={{
        display: "inline-flex",
        flexDirection: "column",
        alignItems: "center",
        justifyContent: "center",
        position: "relative",
      }}
    >
      <div
        className="term-shield-pulse-core"
        style={{
          width: currentSize.container,
          height: currentSize.container,
          position: "relative",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
        }}
      >
        {/* Outer Glowing Pulse Rings */}
        <motion.div
          className="pulse-ring pulse-ring-1"
          style={{
            position: "absolute",
            width: currentSize.pulseRing,
            height: currentSize.pulseRing,
            borderRadius: "50%",
            background:
              "radial-gradient(circle, rgba(115, 87, 255, 0.25) 0%, rgba(115, 87, 255, 0) 70%)",
            pointerEvents: "none",
          }}
          animate={{
            scale: [0.92, 1.12, 0.92],
            opacity: [0.5, 0.9, 0.5],
          }}
          transition={{
            repeat: Infinity,
            duration: 3,
            ease: "easeInOut",
          }}
        />

        <motion.div
          className="pulse-ring pulse-ring-2"
          style={{
            position: "absolute",
            width: currentSize.pulseRing * 0.8,
            height: currentSize.pulseRing * 0.8,
            borderRadius: "50%",
            border: "1px dashed rgba(147, 112, 219, 0.35)",
            pointerEvents: "none",
          }}
          animate={{
            rotate: [0, 360],
          }}
          transition={{
            repeat: Infinity,
            duration: 18,
            ease: "linear",
          }}
        />

        {/* Central Shield Container with Floating Animation */}
        <motion.div
          className="shield-badge-container"
          style={{
            width: currentSize.container,
            height: currentSize.container,
            borderRadius: "26%",
            background:
              "linear-gradient(135deg, rgba(115, 87, 255, 0.95) 0%, rgba(88, 62, 222, 0.98) 100%)",
            boxShadow:
              "0 8px 24px -4px rgba(115, 87, 255, 0.45), 0 0 0 1px rgba(255, 255, 255, 0.22) inset",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            position: "relative",
            zIndex: 2,
          }}
          animate={{
            y: [-3, 3, -3],
          }}
          transition={{
            repeat: Infinity,
            duration: 3.5,
            ease: "easeInOut",
          }}
        >
          <Shield
            size={currentSize.shield}
            color="#ffffff"
            strokeWidth={2.2}
            className="pulse-shield-icon"
          />

          {/* Animated Document/Clause Scan Lines */}
          <div
            className="pulse-doc-lines"
            style={{
              position: "absolute",
              display: "flex",
              flexDirection: "column",
              gap: 2.5,
              alignItems: "center",
              justifyContent: "center",
              width: "55%",
            }}
          >
            <motion.div
              style={{
                height: 2,
                background: "rgba(255, 255, 255, 0.88)",
                borderRadius: 2,
              }}
              animate={{
                width: ["30%", "70%", "30%"],
                opacity: [0.6, 1, 0.6],
              }}
              transition={{
                repeat: Infinity,
                duration: 2.4,
                ease: "easeInOut",
              }}
            />
            <motion.div
              style={{
                height: 2,
                background: "rgba(255, 255, 255, 0.78)",
                borderRadius: 2,
              }}
              animate={{
                width: ["60%", "35%", "60%"],
                opacity: [0.5, 0.9, 0.5],
              }}
              transition={{
                repeat: Infinity,
                duration: 2.8,
                ease: "easeInOut",
                delay: 0.3,
              }}
            />
            <motion.div
              style={{
                height: 2,
                background: "rgba(255, 255, 255, 0.68)",
                borderRadius: 2,
              }}
              animate={{
                width: ["45%", "65%", "45%"],
                opacity: [0.4, 0.8, 0.4],
              }}
              transition={{
                repeat: Infinity,
                duration: 2.2,
                ease: "easeInOut",
                delay: 0.6,
              }}
            />
          </div>
        </motion.div>
      </div>

      {label && (
        <span
          className="term-shield-pulse-label"
          style={{
            marginTop: 10,
            fontSize: 12,
            fontWeight: 600,
            color: "#7357ff",
            letterSpacing: 0.3,
          }}
        >
          {label}
        </span>
      )}
    </div>
  );
}
