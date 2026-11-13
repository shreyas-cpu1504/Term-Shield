import test from "node:test";
import assert from "node:assert";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));

test("Ask My T&C includes Voice-to-Text with Telugu (te-IN) and English (en-IN) support", () => {
  const appPath = path.join(__dirname, "App.jsx");
  const appSource = fs.readFileSync(appPath, "utf-8");

  // Verify voice language codes
  assert.ok(
    appSource.includes('"te-IN"'),
    "AskMyTC must support Telugu speech recognition with language code 'te-IN'"
  );
  assert.ok(
    appSource.includes('"en-IN"'),
    "AskMyTC must support English speech recognition with language code 'en-IN'"
  );

  // Verify Web Speech API initialization with webkit fallback
  assert.ok(
    appSource.includes("window.SpeechRecognition || window.webkitSpeechRecognition"),
    "AskMyTC must use Web Speech API with webkitSpeechRecognition fallback"
  );

  // Verify microphone button and class names
  assert.ok(
    appSource.includes("ask-mic-button"),
    "AskMyTC must render a microphone button with class 'ask-mic-button'"
  );
  assert.ok(
    appSource.includes("ask-voice-lang-group") || appSource.includes("ask-voice-lang-btn"),
    "AskMyTC must provide a language selector between Telugu and English"
  );

  // Verify listening indicator
  assert.ok(
    appSource.includes("ask-voice-listening-bar"),
    "AskMyTC must show a listening indicator while recording"
  );
  assert.ok(
    appSource.includes("Listening in"),
    "AskMyTC listening indicator must indicate the active listening language"
  );

  // Verify stop recording option
  assert.ok(
    appSource.includes("handleStopVoice"),
    "AskMyTC must provide a stop recording action"
  );

  // Verify error handling for permission denial and unsupported browsers
  assert.ok(
    appSource.includes("not-allowed"),
    "AskMyTC must handle microphone permission denial (not-allowed) gracefully"
  );
  assert.ok(
    appSource.includes("Voice recognition is not supported in this browser"),
    "AskMyTC must show a clear fallback error message when Web Speech API is unsupported"
  );

  // Verify recognized text is set into draft without auto-submitting
  assert.ok(
    appSource.includes("setDraft("),
    "AskMyTC must place recognized speech text into the input box draft for editing"
  );
});

test("Ask My T&C preserves existing features and uses same chat API for typed and voice questions", () => {
  const appPath = path.join(__dirname, "App.jsx");
  const appSource = fs.readFileSync(appPath, "utf-8");

  // Verify chat history and Clear Chat are preserved
  assert.ok(
    appSource.includes("fetchHistory") && appSource.includes("getQAHistory"),
    "Chat history fetching must be preserved"
  );
  assert.ok(
    appSource.includes("handleConfirmClearChat") && appSource.includes("clearQAHistory"),
    "Clear Chat functionality must be preserved"
  );

  // Verify ListenButton is preserved
  assert.ok(
    appSource.includes("<ListenButton"),
    "ListenButton audio synthesis must be preserved in assistant messages"
  );

  // Verify suggested questions are preserved
  assert.ok(
    appSource.includes("suggestedQuestions"),
    "Suggested question chips must be preserved"
  );

  // Verify askContractQuestion API is used for question submission
  assert.ok(
    appSource.includes("askContractQuestion("),
    "Typed and voice questions must use the unified askContractQuestion API"
  );
});

test("CSS contains styles for mic button, pulse animation, language selector, and listening indicator", () => {
  const cssPath = path.join(__dirname, "App.css");
  const cssSource = fs.readFileSync(cssPath, "utf-8");

  assert.ok(cssSource.includes(".ask-mic-button"), "CSS must contain .ask-mic-button rules");
  assert.ok(cssSource.includes(".ask-mic-button.is-listening"), "CSS must contain .ask-mic-button.is-listening rules");
  assert.ok(cssSource.includes("ask-mic-pulse"), "CSS must contain microphone pulse animation");
  assert.ok(cssSource.includes(".ask-voice-lang-btn"), "CSS must contain voice language selector button styling");
  assert.ok(cssSource.includes(".ask-voice-listening-bar"), "CSS must contain listening bar styling");
  assert.ok(cssSource.includes(".ask-voice-error-banner"), "CSS must contain voice error banner styling");
});

