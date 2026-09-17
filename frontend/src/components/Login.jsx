import { useState } from "react";
import {
  Eye,
  EyeOff,
  Loader2,
  LogIn,
  ShieldAlert,
} from "lucide-react";

import { loginUser } from "../api/authApi";

const styles = {
  page: {
    minHeight: "100vh",
    display: "grid",
    placeItems: "center",
    padding: "32px 18px",
    background: "linear-gradient(145deg, #f8f7fb 0%, #f1eee8 100%)",
    color: "#24252a",
    fontFamily: "Inter, ui-sans-serif, system-ui, sans-serif",
  },
  panel: {
    width: "min(100%, 430px)",
    padding: "38px",
    border: "1px solid #e2ddd4",
    borderRadius: "18px",
    background: "rgba(255, 255, 255, 0.94)",
    boxShadow: "0 22px 55px rgba(47, 42, 34, 0.11)",
  },
  brandMark: {
    width: "43px",
    height: "43px",
    display: "grid",
    placeItems: "center",
    marginBottom: "24px",
    border: "1px solid #ded5c8",
    borderRadius: "12px",
    background: "#f7eee3",
    color: "#986a37",
  },
  eyebrow: {
    color: "#9a794e",
    fontSize: "10px",
    fontWeight: 800,
    letterSpacing: "1.3px",
  },
  heading: {
    margin: "12px 0 9px",
    color: "#19191f",
    fontSize: "32px",
    lineHeight: 1.08,
    letterSpacing: "-1.5px",
  },
  intro: {
    margin: 0,
    color: "#85827b",
    fontSize: "12px",
    lineHeight: 1.65,
  },
  form: {
    display: "grid",
    gap: "17px",
    marginTop: "29px",
  },
  field: {
    display: "grid",
    gap: "7px",
  },
  label: {
    color: "#625e57",
    fontSize: "10px",
    fontWeight: 750,
  },
  input: {
    width: "100%",
    height: "45px",
    padding: "0 12px",
    border: "1px solid #d9d5cd",
    borderRadius: "9px",
    outline: 0,
    background: "#fff",
    color: "#292a2e",
    fontSize: "12px",
  },
  passwordWrap: {
    position: "relative",
  },
  passwordInput: {
    paddingRight: "44px",
  },
  visibilityButton: {
    position: "absolute",
    top: "50%",
    right: "8px",
    width: "31px",
    height: "31px",
    display: "grid",
    placeItems: "center",
    border: 0,
    borderRadius: "7px",
    background: "transparent",
    color: "#8f8a82",
    cursor: "pointer",
    transform: "translateY(-50%)",
  },
  error: {
    padding: "10px 12px",
    border: "1px solid #efd5d1",
    borderRadius: "8px",
    background: "#fff7f6",
    color: "#bd5c53",
    fontSize: "10px",
    lineHeight: 1.5,
  },
  button: {
    minHeight: "45px",
    display: "inline-flex",
    alignItems: "center",
    justifyContent: "center",
    gap: "8px",
    marginTop: "3px",
    border: "1px solid #292f32",
    borderRadius: "9px",
    background: "#292f32",
    color: "#fff",
    fontSize: "12px",
    fontWeight: 750,
    cursor: "pointer",
  },
  disabledButton: {
    opacity: 0.55,
    cursor: "not-allowed",
  },
  footer: {
    margin: "22px 0 0",
    color: "#aaa69e",
    fontSize: "9px",
    lineHeight: 1.5,
    textAlign: "center",
  },
};

export default function Login({ onLoginSuccess }) {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const handleSubmit = async (event) => {
    event.preventDefault();

    const normalizedEmail = email.trim();

    if (!normalizedEmail || !password) {
      setError("Enter your email and password to continue.");
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

  return (
    <main style={styles.page}>
      <section style={styles.panel} aria-labelledby="login-heading">
        <div style={styles.brandMark}>
          <ShieldAlert size={22} strokeWidth={2.2} />
        </div>

        <span style={styles.eyebrow}>TERM SHIELD WORKSPACE</span>
        <h1 id="login-heading" style={styles.heading}>
          Welcome back.
        </h1>
        <p style={styles.intro}>
          Sign in to review your contracts, risk signals, and important terms.
        </p>

        <form style={styles.form} onSubmit={handleSubmit} noValidate>
          <div style={styles.field}>
            <label htmlFor="login-email" style={styles.label}>
              Email
            </label>
            <input
              id="login-email"
              name="email"
              type="email"
              autoComplete="email"
              value={email}
              onChange={(event) => setEmail(event.target.value)}
              style={styles.input}
              placeholder="you@example.com"
            />
          </div>

          <div style={styles.field}>
            <label htmlFor="login-password" style={styles.label}>
              Password
            </label>
            <div style={styles.passwordWrap}>
              <input
                id="login-password"
                name="password"
                type={showPassword ? "text" : "password"}
                autoComplete="current-password"
                value={password}
                onChange={(event) => setPassword(event.target.value)}
                style={{ ...styles.input, ...styles.passwordInput }}
                placeholder="Enter your password"
              />
              <button
                type="button"
                style={styles.visibilityButton}
                onClick={() => setShowPassword((visible) => !visible)}
                aria-label={showPassword ? "Hide password" : "Show password"}
              >
                {showPassword ? <EyeOff size={16} /> : <Eye size={16} />}
              </button>
            </div>
          </div>

          {error && (
            <div style={styles.error} role="alert">
              {error}
            </div>
          )}

          <button
            type="submit"
            disabled={loading}
            style={{
              ...styles.button,
              ...(loading ? styles.disabledButton : {}),
            }}
          >
            {loading ? (
              <>
                <Loader2 size={16} className="spin" />
                Signing in...
              </>
            ) : (
              <>
                <LogIn size={16} />
                Sign in
              </>
            )}
          </button>
        </form>

        <p style={styles.footer}>
          Your workspace is protected by Term Shield authentication.
        </p>
      </section>
    </main>
  );
}
