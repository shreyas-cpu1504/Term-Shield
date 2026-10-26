import test from "node:test";
import assert from "node:assert";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

import { resolveApiBaseUrl } from "./api/client.js";

const __dirname = path.dirname(fileURLToPath(import.meta.url));

// 1. API Base URL resolution tests
test("resolveApiBaseUrl normalizes production and dev URLs properly", () => {
  assert.strictEqual(
    resolveApiBaseUrl("https://term-shield-vw3i.onrender.com"),
    "https://term-shield-vw3i.onrender.com/api/v1",
    "Appends /api/v1 if missing"
  );

  assert.strictEqual(
    resolveApiBaseUrl("https://term-shield-vw3i.onrender.com/"),
    "https://term-shield-vw3i.onrender.com/api/v1",
    "Strips trailing slash and appends /api/v1"
  );

  assert.strictEqual(
    resolveApiBaseUrl("https://term-shield-vw3i.onrender.com/api/v1/"),
    "https://term-shield-vw3i.onrender.com/api/v1",
    "Preserves existing /api/v1 and removes trailing slash"
  );

  assert.strictEqual(
    resolveApiBaseUrl(""),
    "http://127.0.0.1:8000/api/v1",
    "Falls back to local default when empty"
  );
});

// 2. Register.jsx reliability checks
test("Register.jsx guards against duplicate submits, handles 4xx/5xx/network errors, and resets loading in finally", () => {
  const registerPath = path.join(__dirname, "components", "Register.jsx");
  const registerSource = fs.readFileSync(registerPath, "utf-8");

  // Duplicate submission guard
  assert.ok(
    registerSource.includes("if (loading) return;"),
    "Register.jsx must prevent duplicate form submissions when loading is true"
  );

  // Loading reset in finally
  assert.ok(
    registerSource.includes("finally {\n      setLoading(false);"),
    "Register.jsx must reset loading in a finally block to prevent indefinite spinners"
  );

  // Network and timeout error handling
  assert.ok(
    registerSource.includes("ECONNABORTED") || registerSource.includes("timeout"),
    "Register.jsx must handle timeouts gracefully"
  );
  assert.ok(
    registerSource.includes("Unable to connect to the Term Shield server"),
    "Register.jsx must provide user-readable connection and waking-up guidance"
  );

  // 409 conflict handling
  assert.ok(
    registerSource.includes("status === 409"),
    "Register.jsx must handle duplicate accounts (409 conflict) distinctly"
  );
});

// 3. Login.jsx reliability checks
test("Login.jsx guards against duplicate submits, handles errors cleanly, and resets loading in finally", () => {
  const loginPath = path.join(__dirname, "components", "Login.jsx");
  const loginSource = fs.readFileSync(loginPath, "utf-8");

  // Duplicate submission guard
  assert.ok(
    loginSource.includes("if (loading) return;"),
    "Login.jsx must prevent duplicate form submissions when loading is true"
  );

  // Loading reset in finally
  assert.ok(
    loginSource.includes("finally {\n      setLoading(false);"),
    "Login.jsx must reset loading in a finally block to prevent indefinite spinners"
  );

  // Status-specific errors
  assert.ok(
    loginSource.includes("status === 401"),
    "Login.jsx must handle 401 unauthorized specifically"
  );
  assert.ok(
    loginSource.includes("status >= 500"),
    "Login.jsx must shield users from raw internal 500 stack traces"
  );
});
