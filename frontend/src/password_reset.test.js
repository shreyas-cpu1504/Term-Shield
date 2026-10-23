import test from "node:test";
import assert from "node:assert";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

import { forgotPassword, resetPassword } from "./api/authApi.js";

const __dirname = path.dirname(fileURLToPath(import.meta.url));

// 1. Forgot Password API exports exist
test("forgotPassword and resetPassword API functions are defined", () => {
  assert.strictEqual(typeof forgotPassword, "function");
  assert.strictEqual(typeof resetPassword, "function");
});

// 2. Mock setTimeout behavior is gone from Login.jsx
test("Login.jsx no longer contains setTimeout mock for password reset and calls API", () => {
  const loginPath = path.join(__dirname, "components", "Login.jsx");
  const loginSource = fs.readFileSync(loginPath, "utf-8");

  // Verify setTimeout is NOT in handleForgotSubmit
  const forgotSubmitBlock = loginSource.match(/handleForgotSubmit[\s\S]*?};/);
  assert.ok(forgotSubmitBlock, "handleForgotSubmit function must exist in Login.jsx");

  assert.ok(
    !forgotSubmitBlock[0].includes("setTimeout"),
    "handleForgotSubmit must NOT use setTimeout mock"
  );
  assert.ok(
    forgotSubmitBlock[0].includes("forgotPassword("),
    "handleForgotSubmit must call forgotPassword API"
  );
  assert.ok(
    loginSource.includes("import { loginUser, getAuthProviders, getOAuthLoginUrl, forgotPassword }"),
    "Login.jsx must import forgotPassword from authApi"
  );
});

// 3. ResetPassword component reads token and provides proper fields
test("ResetPassword.jsx reads token, validates inputs, and renders required fields", () => {
  const resetPath = path.join(__dirname, "components", "ResetPassword.jsx");
  const resetSource = fs.readFileSync(resetPath, "utf-8");

  assert.ok(
    resetSource.includes("propToken") && resetSource.includes("URLSearchParams"),
    "ResetPassword must read token from props or URL"
  );
  assert.ok(
    resetSource.includes("new-password") && resetSource.includes("confirm-password"),
    "ResetPassword must provide new-password and confirm-password inputs"
  );
  assert.ok(
    resetSource.includes("resetPassword(token, newPassword)"),
    "ResetPassword must submit to resetPassword API"
  );
  assert.ok(
    resetSource.includes("Minimum 8 characters") && resetSource.includes("Passwords match"),
    "ResetPassword must display password requirements"
  );
});

// 4. ResetPassword handles distinct states: loading, success, invalid/expired token
test("ResetPassword.jsx implements loading, success, and error states", () => {
  const resetPath = path.join(__dirname, "components", "ResetPassword.jsx");
  const resetSource = fs.readFileSync(resetPath, "utf-8");

  assert.ok(
    resetSource.includes("Password reset successfully"),
    "ResetPassword must have success state with clear message"
  );
  assert.ok(
    resetSource.includes("onBackToLogin"),
    "ResetPassword must have return to sign in handler"
  );
  assert.ok(
    resetSource.includes("Updating password..."),
    "ResetPassword must display loading indicator while resetting"
  );
  assert.ok(
    resetSource.includes("No password reset token was found"),
    "ResetPassword must guard against missing or invalid token"
  );
});

// 5. Auth API client implementation check
test("authApi.js defines correct endpoints for forgot-password and reset-password", () => {
  const authApiPath = path.join(__dirname, "api", "authApi.js");
  const authApiSource = fs.readFileSync(authApiPath, "utf-8");

  assert.ok(
    authApiSource.includes("export async function forgotPassword"),
    "Must export forgotPassword"
  );
  assert.ok(
    authApiSource.includes("/auth/forgot-password"),
    "Must POST to /auth/forgot-password"
  );
  assert.ok(
    authApiSource.includes("export async function resetPassword"),
    "Must export resetPassword"
  );
  assert.ok(
    authApiSource.includes("/auth/reset-password"),
    "Must POST to /auth/reset-password"
  );
});

// 6. App.jsx routes to ResetPassword on token query param or path
test("App.jsx routes to ResetPassword on token query parameter or /reset-password path", () => {
  const appPath = path.join(__dirname, "App.jsx");
  const appSource = fs.readFileSync(appPath, "utf-8");

  assert.ok(
    appSource.includes("import ResetPassword from \"./components/ResetPassword\""),
    "App.jsx must import ResetPassword"
  );
  assert.ok(
    appSource.includes("authScreen === \"reset-password\""),
    "App.jsx must handle reset-password auth screen"
  );
  assert.ok(
    appSource.includes("<ResetPassword"),
    "App.jsx must render ResetPassword component"
  );
  assert.ok(
    appSource.includes("params.has(\"token\")") || appSource.includes("urlParams.get(\"token\")"),
    "App.jsx must detect token in URL query"
  );
});
