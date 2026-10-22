import test from "node:test";
import assert from "node:assert";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

import { updateProfile } from "./api/authApi.js";

const __dirname = path.dirname(fileURLToPath(import.meta.url));

// 1. updateProfile API export exists
test("updateProfile API function is defined and exported", () => {
  assert.strictEqual(typeof updateProfile, "function");
});

// 2. authApi.js implementation targets PATCH /auth/profile
test("authApi.js defines updateProfile with /auth/profile endpoint", () => {
  const authApiPath = path.join(__dirname, "api", "authApi.js");
  const authApiSource = fs.readFileSync(authApiPath, "utf-8");

  assert.ok(
    authApiSource.includes("export async function updateProfile"),
    "Must export updateProfile function"
  );
  assert.ok(
    authApiSource.includes('"/auth/profile"') || authApiSource.includes("'/auth/profile'"),
    "Must target /auth/profile endpoint"
  );
});

// 3. App.jsx uses account-scoped storage rather than a single global key
test("App.jsx scopes profile overrides by user ID and purges legacy global key", () => {
  const appPath = path.join(__dirname, "App.jsx");
  const appSource = fs.readFileSync(appPath, "utf-8");

  // Verify account-specific key usage
  assert.ok(
    appSource.includes("termShield_profile_${currentUser.id}"),
    "App.jsx must use account-specific key (e.g. termShield_profile_${currentUser.id})"
  );

  // Verify purging of the legacy global key
  assert.ok(
    appSource.includes('localStorage.removeItem("termShield_profile_override")'),
    "App.jsx must remove legacy global termShield_profile_override key"
  );
});

// 4. In-memory profile data is cleared on logout and session expiration
test("App.jsx clears in-memory profileOverride on logout and session expiration", () => {
  const appPath = path.join(__dirname, "App.jsx");
  const appSource = fs.readFileSync(appPath, "utf-8");

  const logoutBlock = appSource.match(/const handleLogout = \(\) => \{[\s\S]*?\};/);
  assert.ok(logoutBlock, "handleLogout function must exist");
  assert.ok(
    logoutBlock[0].includes("setProfileOverride({})"),
    "handleLogout must clear profileOverride state"
  );
  assert.ok(
    logoutBlock[0].includes("setCurrentUser(null)"),
    "handleLogout must clear currentUser"
  );

  const authExpiredBlock = appSource.match(/const handleAuthExpired = \(event\) => \{[\s\S]*?\};/);
  assert.ok(authExpiredBlock, "handleAuthExpired handler must exist");
  assert.ok(
    authExpiredBlock[0].includes("setProfileOverride({})"),
    "handleAuthExpired must clear profileOverride state"
  );
});

// 5. Display name, photo, and initials dynamically reflect authenticated user
test("App.jsx resolves userDisplayName and userPhoto from authenticated account, never hardcoded", () => {
  const appPath = path.join(__dirname, "App.jsx");
  const appSource = fs.readFileSync(appPath, "utf-8");

  assert.ok(
    !appSource.includes("DUBBASI ADITHYA"),
    "App.jsx must never hardcode DUBBASI ADITHYA"
  );
  assert.ok(
    appSource.includes("currentUser?.profile_photo"),
    "userPhoto must check currentUser?.profile_photo from backend"
  );
  assert.ok(
    appSource.includes("currentUser?.full_name"),
    "Display name must check currentUser?.full_name"
  );
});

// 6. EditProfileModal includes validation, async saving, and read-only email
test("EditProfileModal validates name length, prevents empty names, and keeps email read-only", () => {
  const appPath = path.join(__dirname, "App.jsx");
  const appSource = fs.readFileSync(appPath, "utf-8");

  assert.ok(
    appSource.includes("function EditProfileModal"),
    "EditProfileModal component must exist"
  );
  assert.ok(
    appSource.includes("trimmed.length < 2") && appSource.includes("trimmed.length > 100"),
    "EditProfileModal must validate name min and max lengths"
  );
  assert.ok(
    appSource.includes("readOnly") && appSource.includes("disabled"),
    "Email field must be readOnly and disabled"
  );
  assert.ok(
    appSource.includes("handleRemovePhoto"),
    "EditProfileModal must have handleRemovePhoto handler"
  );
  assert.ok(
    appSource.includes("isSaving"),
    "EditProfileModal must provide loading state while saving"
  );
});
