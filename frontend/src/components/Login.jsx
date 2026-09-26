import { useState, useEffect } from "react";
import {
  Mail,
  Lock,
  Eye,
  EyeOff,
  Loader2,
  LogIn,
  AlertCircle,
  CheckCircle2,
  Info,
  X,
  ArrowLeft,
  KeyRound,
} from "lucide-react";

import { loginUser, getAuthProviders, getOAuthLoginUrl } from "../api/authApi";
import TermShieldLogo from "./TermShieldLogo";
import "./Login.css";

export default function Login({ onLoginSuccess, onSwitchToRegister, initialNotice }) {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(initialNotice || "");
  const [oauthNotice, setOauthNotice] = useState(null);
  const [providers, setProviders] = useState(null);

  // Dedicated Forgot Password flow state
  const [isForgotPassword, setIsForgotPassword] = useState(false);
  const [forgotEmail, setForgotEmail] = useState("");
  const [forgotLoading, setForgotLoading] = useState(false);
  const [forgotError, setForgotError] = useState("");
  const [forgotSuccess, setForgotSuccess] = useState(false);

  // Check backend OAuth configuration status on mount
  useEffect(() => {
    getAuthProviders()
      .then((data) => setProviders(data))
      .catch(() => {
        // Backend not reachable yet or default state
      });
  }, []);

  const handleOpenForgotPassword = () => {
    setError("");
    setForgotError("");
    setForgotSuccess(false);
    setForgotEmail(email);
    setIsForgotPassword(true);
  };

  const handleBackToLogin = () => {
    setError("");
    setForgotError("");
    setForgotSuccess(false);
    setIsForgotPassword(false);
  };

  const handleForgotSubmit = (event) => {
    event.preventDefault();
    const normalized = (forgotEmail || email).trim();

    if (!normalized) {
      setForgotError("Enter your email address to receive reset instructions.");
      return;
    }

    if (!/^\S+@\S+\.\S+$/.test(normalized)) {
      setForgotError("Enter a valid email address.");
      return;
    }

    setForgotLoading(true);
    setForgotError("");

    // Simulate sending reset email while preserving security privacy
    setTimeout(() => {
      setForgotLoading(false);
      setForgotSuccess(true);
    }, 500);
  };

  const handleSubmit = async (event) => {
    event.preventDefault();

    const normalizedEmail = email.trim();

    if (!normalizedEmail || !password) {
      setError("Enter your email address and password to continue.");
      return;
    }

    if (!/^\S+@\S+\.\S+$/.test(normalizedEmail)) {
      setError("Enter a valid email address.");
      return;
    }

    setLoading(true);
    setError("");

    try {
      const response = await loginUser({
        email: normalizedEmail,
        password,
      });

      if (!response?.access_token) {
        throw new Error("The login response did not include an access token.");
      }

      localStorage.setItem("termShieldToken", response.access_token);
      onLoginSuccess?.(response);
    } catch (requestError) {
      setError(
        requestError?.response?.data?.detail ||
          requestError?.response?.data?.message ||
          requestError?.message ||
          "Unable to sign in. Check your credentials and try again."
      );
    } finally {
      setLoading(false);
    }
  };

  const handleOAuthClick = (providerKey, providerName) => {
    setError("");
    setOauthNotice(null);

    // If providers status is known from backend and unconfigured, guide user clearly
    if (providers && providers[providerKey] && !providers[providerKey].enabled) {
      setOauthNotice(
        `${providerName} OAuth is not yet configured in backend environment variables. Please set GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET in backend/.env.`
      );
      return;
    }

    // Real OAuth 2.0 / OIDC redirect to backend authorization endpoint
    const redirectUrl = getOAuthLoginUrl(providerKey);
    window.location.href = redirectUrl;
  };

  return (
    <main className="ts-login-page">
      {/* Background Soft Wave Ambience */}
      <div className="ts-login-bg-decor" aria-hidden="true">
        <div className="ts-login-wave-ribbon" />
        <div className="ts-login-wave-accent-right" />
      </div>

      {/* Top Navigation Row */}
      <header className="ts-login-top-bar">
        <div className="ts-login-top-script">
          Contracts made simple. Decisions made clearer.
        </div>
        <div className="ts-login-top-nav">
          AI &nbsp;|&nbsp; LAW &nbsp;|&nbsp; PEOPLE &nbsp;|&nbsp; A SAFER TOMORROW
        </div>
      </header>

      {/* Main Center Area */}
      <div className="ts-login-main-container">
        {/* Right Desktop Visual Accent (from Reference Image) */}
        <aside className="ts-login-right-decor" aria-hidden="true">
          <div className="ts-login-vertical-tagline">
            <span>REVIEW.</span>
            <span>UNDERSTAND.</span>
            <span>AGREE.</span>
            <span>CONFIDENTLY.</span>
          </div>
          <div className="ts-login-book-stack-badge">
            Better Terms
            <span>Brighter Futures</span>
          </div>
        </aside>

        {/* Center Card Wrapper */}
        <div className="ts-login-card-wrapper">
          {/* Header with Term Shield Logo & Branding */}
          <section className="ts-login-header">
            <div className="ts-login-logo-container">
              <TermShieldLogo size={52} glow={true} showAura={true} showOrbitalRing={true} />
            </div>

            <h1 className="ts-login-wordmark">
              <span className="ts-login-wordmark-term">Term</span>
              <span className="ts-login-wordmark-shield">Shield</span>
            </h1>

            <div className="ts-login-tagline">
              Simple Contracts. Stronger Decisions.
            </div>

            <p className="ts-login-subtext">
              AI-powered clarity for every contract.
            </p>
          </section>

          {/* Glassmorphic White Login Card */}
          <section className="ts-login-panel" aria-labelledby="form-heading">
            <h2 id="form-heading" className="sr-only" style={{ display: "none" }}>
              {isForgotPassword ? "Reset Password Form" : "Sign In Form"}
            </h2>

            {isForgotPassword ? (
              /* DEDICATED FORGOT PASSWORD FORM */
              <div className="ts-forgot-flow-container">
                <div className="ts-forgot-header">
                  <button
                    type="button"
                    className="ts-forgot-pass-link"
                    onClick={handleBackToLogin}
                    style={{
                      display: "inline-flex",
                      alignItems: "center",
                      gap: "6px",
                      marginBottom: "12px",
                      cursor: "pointer",
                    }}
                  >
                    <ArrowLeft size={14} />
                    <span>Back to sign in</span>
                  </button>
                  <h3 className="ts-forgot-title">Reset your password</h3>
                  <p className="ts-forgot-subtext">
                    Enter the email associated with your account to receive password reset instructions.
                  </p>
                </div>

                {forgotSuccess ? (
                  /* POST-SUBMISSION: Informational / Success Message */
                  <div style={{ display: "flex", flexDirection: "column", gap: "16px" }}>
                    <div className="ts-alert-banner success" role="status">
                      <CheckCircle2 size={16} />
                      <div className="ts-alert-content">
                        <strong>Reset instructions sent</strong>
                        <p>
                          Password reset instructions will be sent to your email address if an account exists.
                        </p>
                      </div>
                    </div>

                    <button
                      type="button"
                      onClick={handleBackToLogin}
                      className="ts-primary-btn"
                    >
                      <LogIn size={16} />
                      <span>Return to sign in</span>
                    </button>
                  </div>
                ) : (
                  /* PRE-SUBMISSION: Input form without any premature message */
                  <form className="ts-login-form" onSubmit={handleForgotSubmit} noValidate>
                    <div className="ts-input-wrap">
                      <span className="ts-input-icon-left" aria-hidden="true">
                        <Mail size={16} strokeWidth={2} />
                      </span>
                      <input
                        id="forgot-email"
                        name="email"
                        type="email"
                        autoComplete="email"
                        value={forgotEmail}
                        onChange={(event) => {
                          setForgotEmail(event.target.value);
                          if (forgotError) setForgotError("");
                        }}
                        className="ts-form-input"
                        placeholder="Email address"
                        aria-label="Email address for password reset"
                        required
                      />
                    </div>

                    {forgotError && (
                      <div className="ts-alert-banner error" role="alert">
                        <AlertCircle size={16} />
                        <span>{forgotError}</span>
                      </div>
                    )}

                    <button
                      type="submit"
                      disabled={forgotLoading}
                      className="ts-primary-btn"
                      aria-busy={forgotLoading}
                    >
                      {forgotLoading ? (
                        <>
                          <Loader2 size={16} className="spin" />
                          <span>Sending instructions...</span>
                        </>
                      ) : (
                        <>
                          <KeyRound size={16} />
                          <span>Send reset instructions</span>
                        </>
                      )}
                    </button>

                    <button
                      type="button"
                      onClick={handleBackToLogin}
                      className="ts-secondary-btn"
                    >
                      Cancel
                    </button>
                  </form>
                )}
              </div>
            ) : (
              /* STANDARD LOGIN FORM */
              <>
                <form className="ts-login-form" onSubmit={handleSubmit} noValidate>
                  {/* Email Address Field with Mail Icon */}
                  <div className="ts-input-wrap">
                    <span className="ts-input-icon-left" aria-hidden="true">
                      <Mail size={16} strokeWidth={2} />
                    </span>
                    <input
                      id="login-email"
                      name="email"
                      type="email"
                      autoComplete="email"
                      value={email}
                      onChange={(event) => {
                        setEmail(event.target.value);
                        if (error) setError("");
                      }}
                      className="ts-form-input"
                      placeholder="Email address"
                      aria-label="Email address"
                      required
                    />
                  </div>

                  {/* Password Field with Lock Icon and Eye Toggle */}
                  <div className="ts-input-wrap">
                    <span className="ts-input-icon-left" aria-hidden="true">
                      <Lock size={16} strokeWidth={2} />
                    </span>
                    <input
                      id="login-password"
                      name="password"
                      type={showPassword ? "text" : "password"}
                      autoComplete="current-password"
                      value={password}
                      onChange={(event) => {
                        setPassword(event.target.value);
                        if (error) setError("");
                      }}
                      className="ts-form-input"
                      placeholder="Password"
                      aria-label="Password"
                      style={{ paddingRight: "44px" }}
                      required
                    />
                    <button
                      type="button"
                      className="ts-visibility-btn"
                      onClick={() => setShowPassword((visible) => !visible)}
                      aria-label={showPassword ? "Hide password" : "Show password"}
                    >
                      {showPassword ? <EyeOff size={16} /> : <Eye size={16} />}
                    </button>
                  </div>

                  {/* Forgot Password Link */}
                  <div className="ts-forgot-pass-row">
                    <button
                      type="button"
                      className="ts-forgot-pass-link"
                      onClick={handleOpenForgotPassword}
                    >
                      Forgot password?
                    </button>
                  </div>

                  {/* Error Banner */}
                  {error && (
                    <div className="ts-alert-banner error" role="alert">
                      <AlertCircle size={16} />
                      <span>{error}</span>
                    </div>
                  )}

                  {/* OAuth Configuration Notice */}
                  {oauthNotice && (
                    <div className="ts-alert-banner info" role="status">
                      <Info size={16} />
                      <div style={{ flex: 1 }}>{oauthNotice}</div>
                      <button
                        type="button"
                        onClick={() => setOauthNotice(null)}
                        style={{
                          background: "transparent",
                          border: "none",
                          padding: 0,
                          cursor: "pointer",
                          color: "#1d4ed8",
                          display: "grid",
                          placeItems: "center",
                        }}
                        aria-label="Dismiss notice"
                      >
                        <X size={14} />
                      </button>
                    </div>
                  )}

                  {/* Primary Sign In Button with Electric Blue to Purple Gradient */}
                  <button
                    type="submit"
                    disabled={loading}
                    className="ts-primary-btn"
                    aria-busy={loading}
                  >
                    {loading ? (
                      <>
                        <Loader2 size={16} className="spin" />
                        <span>Signing in...</span>
                      </>
                    ) : (
                      <>
                        <LogIn size={16} />
                        <span>Sign in</span>
                      </>
                    )}
                  </button>

                  {/* Divider */}
                  <div className="ts-oauth-divider" aria-hidden="true">
                    <span className="ts-oauth-divider-line" />
                    <span className="ts-oauth-divider-text">OR CONTINUE WITH</span>
                    <span className="ts-oauth-divider-line" />
                  </div>

                  {/* OAuth Providers Group */}
                  <div className="ts-oauth-group">
                    {/* Continue with Google */}
                    <button
                      type="button"
                      className="ts-oauth-btn"
                      onClick={() => handleOAuthClick("google", "Google")}
                      aria-label="Continue with Google"
                    >
                      <svg
                        className="ts-oauth-icon"
                        viewBox="0 0 24 24"
                        aria-hidden="true"
                      >
                        <path
                          d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"
                          fill="#4285F4"
                        />
                        <path
                          d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"
                          fill="#34A853"
                        />
                        <path
                          d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.06H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.94l2.85-2.22.81-.63z"
                          fill="#FBBC05"
                        />
                        <path
                          d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.06l3.66 2.84c.87-2.6 3.3-4.52 6.16-4.52z"
                          fill="#EA4335"
                        />
                      </svg>
                      <span>Continue with Google</span>
                    </button>
                  </div>
                </form>

                {/* Account Switcher Footer */}
                <div className="ts-card-account-switch">
                  <span>New to Term Shield?</span>
                  <button
                    type="button"
                    onClick={onSwitchToRegister}
                    className="ts-switch-btn"
                  >
                    Create account
                  </button>
                </div>
              </>
            )}
          </section>
        </div>
      </div>

      {/* Bottom Subtle Footer */}
      <footer className="ts-login-bottom-bar">
        Contracts made simple. Decisions made clearer.
      </footer>
    </main>
  );
}
