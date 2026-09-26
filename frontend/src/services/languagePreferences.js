/**
 * Language and Accessibility Preferences Service for Term Shield.
 * Manages localStorage persistence for user language, information delivery,
 * explanation style, and primary use preferences.
 */

export const LEGACY_LANGUAGE_STORAGE_KEY = "termShield_language_preferences";
export const LANGUAGE_STORAGE_KEY = LEGACY_LANGUAGE_STORAGE_KEY;

export const SUPPORTED_LANGUAGES = [
  { code: "en", label: "English", native: "English", bcp47: "en-IN", fallbackBcp47: "en-US" },
  { code: "te", label: "Telugu", native: "తెలుగు (Telugu)", bcp47: "te-IN" },
  { code: "hi", label: "Hindi", native: "हिन्दी (Hindi)", bcp47: "hi-IN" },
  { code: "ta", label: "Tamil", native: "தமிழ் (Tamil)", bcp47: "ta-IN" },
  { code: "kn", label: "Kannada", native: "ಕನ್ನಡ (Kannada)", bcp47: "kn-IN" },
  { code: "ml", label: "Malayalam", native: "മലയാളം (Malayalam)", bcp47: "ml-IN" },
  { code: "mr", label: "Marathi", native: "मराठी (Marathi)", bcp47: "mr-IN" },
  { code: "bn", label: "Bengali", native: "বাংলা (Bengali)", bcp47: "bn-IN" },
  { code: "gu", label: "Gujarati", native: "ગુજરાતી (Gujarati)", bcp47: "gu-IN" },
  { code: "ur", label: "Urdu", native: "اردو (Urdu)", bcp47: "ur-IN", fallbackBcp47: "ur-PK" },
];

export const INFO_PREFERENCES = [
  { id: "Read", label: "Read", description: "I prefer reading information." },
  { id: "Listen", label: "Listen", description: "I prefer listening to information." },
  { id: "Read + Listen", label: "Read + Listen", description: "I want both." },
];

export const EXPLANATION_STYLES = [
  { id: "Standard", label: "Standard", description: "Use normal contract terminology." },
  { id: "Simple", label: "Simple", description: "Explain legal terms using easy everyday language." },
];

export const PRIMARY_USES = [
  "Understanding contracts",
  "Checking contract risks",
  "Understanding payments and fees",
  "Understanding my responsibilities",
  "All of these",
];

export const DEFAULT_LANGUAGE_PREFERENCES = {
  language: "English",
  infoPreference: "Read + Listen",
  explanationStyle: "Standard",
  primaryUse: "All of these",
  onboardingCompleted: true,
};

/**
 * Resolve a stable identifier string from a user object or string identifier.
 * Priority: user.id -> user.email -> string value.
 */
export function resolveUserKey(userOrId) {
  if (!userOrId) return null;
  if (typeof userOrId === "object") {
    return userOrId.id || userOrId.email || null;
  }
  return String(userOrId).trim() || null;
}

/**
 * Generate a safe, per-user localStorage key for preferences.
 */
export function getPreferencesStorageKey(userId) {
  if (!userId) return LEGACY_LANGUAGE_STORAGE_KEY;
  const cleanId = String(userId).trim().toLowerCase().replace(/[^a-z0-9@._-]/g, "_");
  return `termShield_language_preferences_${cleanId}`;
}

/**
 * Retrieve saved language preferences or default values for a given user.
 * Seamlessly migrates legacy global preferences to the user's personal key
 * on first authenticated access.
 */
export function getLanguagePreferences(userOrId) {
  const userId = resolveUserKey(userOrId);
  const targetKey = getPreferencesStorageKey(userId);

  try {
    let stored = localStorage.getItem(targetKey);

    // Migration: If user key is missing but legacy global key exists, migrate it
    if (!stored && userId) {
      const legacy = localStorage.getItem(LEGACY_LANGUAGE_STORAGE_KEY);
      if (legacy) {
        stored = legacy;
        localStorage.setItem(targetKey, legacy);
        localStorage.removeItem(LEGACY_LANGUAGE_STORAGE_KEY);
      }
    }

    if (stored) {
      const parsed = JSON.parse(stored);
      return {
        ...DEFAULT_LANGUAGE_PREFERENCES,
        ...parsed,
        onboardingCompleted: Boolean(parsed.onboardingCompleted),
      };
    }
  } catch (err) {
    console.error("Failed to read language preferences:", err);
  }

  return { ...DEFAULT_LANGUAGE_PREFERENCES, onboardingCompleted: false };
}

/**
 * Check if the specified user has completed onboarding.
 * If unauthenticated or no userId is provided, returns false so that
 * the user is evaluated once authentication is established.
 */
export function hasCompletedOnboarding(userOrId) {
  const userId = resolveUserKey(userOrId);
  if (!userId) {
    return false;
  }

  const targetKey = getPreferencesStorageKey(userId);
  try {
    let stored = localStorage.getItem(targetKey);

    // Check legacy migration
    if (!stored) {
      const legacy = localStorage.getItem(LEGACY_LANGUAGE_STORAGE_KEY);
      if (legacy) {
        stored = legacy;
        localStorage.setItem(targetKey, legacy);
        localStorage.removeItem(LEGACY_LANGUAGE_STORAGE_KEY);
      }
    }

    if (!stored) return false;
    const parsed = JSON.parse(stored);
    return Boolean(parsed?.onboardingCompleted);
  } catch {
    return false;
  }
}

/**
 * Save language preferences to per-user localStorage.
 */
export function saveLanguagePreferences(prefs, userOrId) {
  const userId = resolveUserKey(userOrId);
  const targetKey = getPreferencesStorageKey(userId);

  try {
    const current = getLanguagePreferences(userId);
    const updated = {
      ...current,
      ...prefs,
      onboardingCompleted: true,
    };
    localStorage.setItem(targetKey, JSON.stringify(updated));

    // Dispatch custom event for reactive updates across components
    if (typeof window !== "undefined") {
      window.dispatchEvent(
        new CustomEvent("termshield_preferences_changed", {
          detail: { ...updated, userId },
        })
      );
    }
    return updated;
  } catch (err) {
    console.error("Failed to save language preferences:", err);
    return prefs;
  }
}

/**
 * Reset accessibility & language preferences to default values for a user
 * without wiping user authentication, name, or profile photo.
 */
export function resetLanguagePreferences(userOrId) {
  const userId = resolveUserKey(userOrId);
  const targetKey = getPreferencesStorageKey(userId);

  try {
    const reset = {
      language: "English",
      infoPreference: "Read + Listen",
      explanationStyle: "Standard",
      primaryUse: "All of these",
      onboardingCompleted: true,
    };
    localStorage.setItem(targetKey, JSON.stringify(reset));
    if (typeof window !== "undefined") {
      window.dispatchEvent(
        new CustomEvent("termshield_preferences_changed", {
          detail: { ...reset, userId },
        })
      );
    }
    return reset;
  } catch (err) {
    console.error("Failed to reset language preferences:", err);
    return DEFAULT_LANGUAGE_PREFERENCES;
  }
}

/**
 * Detect script language of a given text string for accurate TTS voice matching.
 * This ensures Telugu text is spoken with Telugu voice, Hindi with Hindi voice,
 * and mixed sentences (Telugu + English legal terms) are spoken naturally in full.
 */
export function detectScriptLanguage(text, preferredLang = null) {
  if (!text || typeof text !== "string") return "en-IN";

  const scripts = [
    { code: "te-IN", lang: "te", regex: /[\u0C00-\u0C7F]/g }, // Telugu
    { code: "ta-IN", lang: "ta", regex: /[\u0B80-\u0BFF]/g }, // Tamil
    { code: "kn-IN", lang: "kn", regex: /[\u0C80-\u0CFF]/g }, // Kannada
    { code: "ml-IN", lang: "ml", regex: /[\u0D00-\u0D7F]/g }, // Malayalam
    { code: "bn-IN", lang: "bn", regex: /[\u0980-\u09FF]/g }, // Bengali
    { code: "gu-IN", lang: "gu", regex: /[\u0A80-\u0AFF]/g }, // Gujarati
    { code: "ur-IN", lang: "ur", regex: /[\u0600-\u06FF]/g }, // Urdu / Arabic
    { code: "hi-IN", lang: "hi", regex: /[\u0900-\u097F]/g }, // Devanagari (Hindi / Marathi)
  ];

  const counts = {};
  for (const s of scripts) {
    const matches = text.match(s.regex);
    if (matches && matches.length > 0) {
      counts[s.code] = matches.length;
    }
  }

  const detectedCodes = Object.keys(counts);
  if (detectedCodes.length > 0) {
    // If preferred language matches one of the detected scripts, prioritize it
    if (preferredLang) {
      const normPref = String(preferredLang).toLowerCase();
      if (normPref.includes("marathi") && counts["hi-IN"]) {
        return "mr-IN";
      }
      for (const code of detectedCodes) {
        const langPart = code.split("-")[0];
        if (normPref.includes(langPart)) {
          return code;
        }
      }
      const match = SUPPORTED_LANGUAGES.find(
        (l) => l.label.toLowerCase() === normPref || l.code.toLowerCase() === normPref
      );
      if (match && counts[match.bcp47]) {
        return match.bcp47;
      }
    }

    if (preferredLang && String(preferredLang).toLowerCase().includes("marathi") && counts["hi-IN"]) {
      return "mr-IN";
    }

    // Pick dominant script by count
    return detectedCodes.sort((a, b) => counts[b] - counts[a])[0];
  }

  // If no Indic script, return English
  return "en-IN";
}

/**
 * Map formal contract clause categories to plain-language helper descriptions
 * when "Simple" explanation style is enabled.
 */
export const CATEGORY_SIMPLE_EXPLANATIONS = {
  liability: "Who is responsible if something goes wrong?",
  termination: "How and when can this contract be ended?",
  indemnification: "Who may have to pay for certain losses or claims?",
  indemnity: "Who may have to pay for certain losses or claims?",
  payment: "What money must be paid, when, and how?",
  payments: "What money must be paid, when, and how?",
  fee: "What fees or charges apply to you?",
  fees: "What fees or charges apply to you?",
  confidentiality: "What private information must be kept secret?",
  "governing law": "Which laws and courts handle any legal dispute?",
  jurisdiction: "Which courts have the power to decide disputes?",
  "intellectual property": "Who owns the work, content, or technology?",
  ip: "Who owns the work, content, or technology?",
  "force majeure": "What happens if unexpected disasters stop performance?",
  warranty: "What promises and guarantees are being made?",
  warranties: "What promises and guarantees are being made?",
  "dispute resolution": "How will disagreements or arguments be settled?",
  arbitration: "How private neutral arbitrators settle disputes outside court.",
  "non-compete": "What future business activities or jobs are restricted?",
  restriction: "What actions or rights are limited under this agreement?",
  renewal: "How does the contract continue or automatically renew?",
  obligation: "What duties and responsibilities are you required to follow?",
  obligations: "What duties and responsibilities are you required to follow?",
  remedy: "What rights or compensation do you get if the agreement is broken?",
  amendment: "How changes or updates can be made to this contract.",
};

/**
 * Get simple helper description for a category if available.
 */
export function getSimpleCategoryHelper(categoryName) {
  if (!categoryName || typeof categoryName !== "string") return null;
  const key = categoryName.trim().toLowerCase();

  // Direct match
  if (CATEGORY_SIMPLE_EXPLANATIONS[key]) {
    return CATEGORY_SIMPLE_EXPLANATIONS[key];
  }

  // Partial substring match
  for (const [cat, desc] of Object.entries(CATEGORY_SIMPLE_EXPLANATIONS)) {
    if (key.includes(cat)) {
      return desc;
    }
  }

  return null;
}
