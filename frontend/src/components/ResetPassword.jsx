import { useState, useEffect } from "react";
import {
  Lock,
  Eye,
  EyeOff,
  Loader2,
  CheckCircle2,
  AlertCircle,
  ArrowLeft,
  KeyRound,
  ShieldCheck,
  LogIn,
} from "lucide-react";

import { resetPassword } from "../api/authApi";
import TermShieldLogo from "./TermShieldLogo";
import "./Login.css";

export default function ResetPassword({ token: propToken, onBackToLogin }) {
  const [token, setToken] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [showNewPassword, setShowNewPassword] = useState(false);
  const [showConfirmPassword, setShowConfirmPassword] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState(false);

  useEffect(() => {
    // Read token from props or directly from URL search params
    const resolvedToken =
      propToken ||
      (typeof window !== "undefined"
        ? new URLSearchParams(window.location.search).get("token")
        : null);

    if (resolvedToken && resolvedToken.trim()) {
      setToken(resolvedToken.trim());
    } else {
      setError("No password reset token was found in the link. Please request a new password reset.");
    }
  }, [propToken]);

  const hasMinLength = newPassword.length >= 8;
  const passwordsMatch = newPassword.length > 0 && newPassword === confirmPassword;

  const handleSubmit = async (event) => {
    event.preventDefault();

    if (!token) {
      setError("Invalid or missing password reset token. Please request a new link.");
      return;
    }

    if (!newPassword) {
      setError("Enter your new password.");
      return;
    }

    if (newPassword.length < 8) {
      setError("Password must be at least 8 characters long.");
      return;
    }

    if (newPassword.length > 128) {
      setError("Password must be 128 characters or fewer.");
      return;
    }

    if (newPassword !== confirmPassword) {
      setError("Passwords do not match.");
      return;
    }

    setLoading(true);
    setError("");

    try {
      await resetPassword(token, newPassword);
      setSuccess(true);
    } catch (err) {
      const msg =
        err?.response?.data?.detail ||
        err?.response?.data?.message ||
        "Unable to reset password. The link may be invalid or expired.";
      setError(msg);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="ts-login-page">
      {/* Background Architectural Glows */}
      <div className="ts-login-bg-decor" aria-hidden="true">
        <div className="ts-login-wave-ribbon" />
        <div className="ts-login-wave-accent-right" />
      </div>

      {/* Top Header */}
      <header className="ts-login-top-bar">
        <div className="ts-login-top-script">Term Shield</div>
        <div className="ts-login-top-nav">ACCOUNT RECOVERY</div>
      </header>

      {/* Main Container */}
      <main className="ts-login-main-container">
        <div className="ts-login-card">
          <div className="ts-login-card-content">
            <div className="ts-brand-badge-wrap">
              <TermShieldLogo size={36} />
            </div>

            <div className="ts-forgot-header">
              {onBackToLogin && !success && (
                <button
                  type="button"
                  onClick={onBackToLogin}
                  className="ts-forgot-pass-link"
                  style={{
                    display: "inline-flex",
                    alignItems: "center",
                    gap: "6px",
                    marginBottom: "12px",
                  }}
                >
                  <ArrowLeft size={14} />
                  <span>Back to sign in</span>
                </button>
              )}
              <h3 className="ts-forgot-title">Set new password</h3>
              <p className="ts-forgot-subtext">
                Create a strong new password for your Term Shield account.
              </p>
            </div>

            {/* Error Notification */}
            {error && (
              <div className="ts-alert-banner error" role="alert" style={{ marginBottom: "16px" }}>
                <AlertCircle size={16} />
                <div className="ts-alert-content">
                  <p>{error}</p>
                </div>
              </div>
            )}

            {/* Success State */}
            {success ? (
              <div style={{ display: "flex", flexDirection: "column", gap: "16px" }}>
                <div className="ts-alert-banner success" role="status">
                  <CheckCircle2 size={18} />
                  <div className="ts-alert-content">
                    <strong>Password reset successfully</strong>
                    <p>
                      Your password has been securely updated. You can now sign in with your new password.
                    </p>
                  </div>
                </div>

                <button
                  type="button"
                  onClick={onBackToLogin}
                  className="ts-primary-btn"
                >
                  <LogIn size={16} />
                  <span>Return to sign in</span>
                </button>
              </div>
            ) : !token ? (
              /* Missing Token State */
              <div style={{ display: "flex", flexDirection: "column", gap: "16px" }}>
                <button
                  type="button"
                  onClick={onBackToLogin}
                  className="ts-primary-btn"
                >
                  <ArrowLeft size={16} />
                  <span>Go to sign in</span>
                </button>
              </div>
            ) : (
              /* Reset Form */
              <form className="ts-login-form" onSubmit={handleSubmit} noValidate>
                {/* New Password Input */}
                <div className="ts-field-group">
                  <label className="ts-field-label" htmlFor="new-password">
                    New Password
                  </label>
                  <div className="ts-input-wrap">
                    <span className="ts-input-icon-left" aria-hidden="true">
                      <Lock size={16} strokeWidth={2} />
                    </span>
                    <input
                      id="new-password"
                      name="new-password"
                      type={showNewPassword ? "text" : "password"}
                      autoComplete="new-password"
                      placeholder="At least 8 characters"
                      className="ts-form-input has-left-icon has-right-icon"
                      value={newPassword}
                      onChange={(e) => {
                        setNewPassword(e.target.value);
                        if (error) setError("");
                      }}
                      disabled={loading}
                      required
                    />
                    <button
                      type="button"
                      className="ts-visibility-btn"
                      onClick={() => setShowNewPassword(!showNewPassword)}
                      aria-label={showNewPassword ? "Hide password" : "Show password"}
                      tabIndex={-1}
                    >
                      {showNewPassword ? <EyeOff size={16} /> : <Eye size={16} />}
                    </button>
                  </div>
                </div>

                {/* Confirm Password Input */}
                <div className="ts-field-group">
                  <label className="ts-field-label" htmlFor="confirm-password">
                    Confirm New Password
                  </label>
                  <div className="ts-input-wrap">
                    <span className="ts-input-icon-left" aria-hidden="true">
                      <ShieldCheck size={16} strokeWidth={2} />
                    </span>
                    <input
                      id="confirm-password"
                      name="confirm-password"
                      type={showConfirmPassword ? "text" : "password"}
                      autoComplete="new-password"
                      placeholder="Re-enter new password"
                      className="ts-form-input has-left-icon has-right-icon"
                      value={confirmPassword}
                      onChange={(e) => {
                        setConfirmPassword(e.target.value);
                        if (error) setError("");
                      }}
                      disabled={loading}
                      required
                    />
                    <button
                      type="button"
                      className="ts-visibility-btn"
                      onClick={() => setShowConfirmPassword(!showConfirmPassword)}
                      aria-label={showConfirmPassword ? "Hide password" : "Show password"}
                      tabIndex={-1}
                    >
                      {showConfirmPassword ? <EyeOff size={16} /> : <Eye size={16} />}
                    </button>
                  </div>
                </div>

                {/* Password Requirements Checklist */}
                <div
                  style={{
                    backgroundColor: "rgba(15, 23, 42, 0.6)",
                    border: "1px solid #1e293b",
                    borderRadius: "8px",
                    padding: "10px 14px",
                    display: "flex",
                    flexDirection: "column",
                    gap: "6px",
                    fontSize: "12px",
                  }}
                >
                  <div
                    style={{
                      display: "flex",
                      alignItems: "center",
                      gap: "8px",
                      color: hasMinLength ? "#10b981" : "#94a3b8",
                    }}
                  >
                    <CheckCircle2 size={13} style={{ opacity: hasMinLength ? 1 : 0.4 }} />
                    <span>Minimum 8 characters</span>
                  </div>
                  <div
                    style={{
                      display: "flex",
                      alignItems: "center",
                      gap: "8px",
                      color: passwordsMatch ? "#10b981" : "#94a3b8",
                    }}
                  >
                    <CheckCircle2 size={13} style={{ opacity: passwordsMatch ? 1 : 0.4 }} />
                    <span>Passwords match</span>
                  </div>
                </div>

                {/* Submit Button */}
                <button
                  type="submit"
                  className="ts-primary-btn"
                  disabled={loading || !hasMinLength || !passwordsMatch}
                  aria-busy={loading}
                >
                  {loading ? (
                    <>
                      <Loader2 size={16} className="spin" />
                      <span>Updating password...</span>
                    </>
                  ) : (
                    <>
                      <KeyRound size={16} />
                      <span>Reset password</span>
                    </>
                  )}
                </button>
              </form>
            )}
          </div>
        </div>
      </main>
    </div>
  );
}
