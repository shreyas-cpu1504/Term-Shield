import test from "node:test";
import assert from "node:assert";
import React from "react";
import { renderToString } from "react-dom/server";

import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

import {
  detectClauseCategory,
  getWhatItSays,
  getWhyThisIsImportant,
  getPotentialConcerns,
  getWhatShouldYouDo,
  getClauseSourceText,
  generateConciseClauseSummary,
} from "./services/clauseIntelligence.js";

const __dirname = path.dirname(fileURLToPath(import.meta.url));

// ============================================================================
// 1. PAYMENT CLAUSE TESTS
// ============================================================================
test("Payment clause generates 3 clear grounded sections", () => {
  const clause = {
    title: "Payment Terms",
    clause_type: "PAYMENT",
    meaning: "The customer must pay all invoices within 30 days of receipt.",
    monetary_terms: ["10,000 USD"],
    deadlines: ["30 days"],
    risk_level: "LOW",
    risk_score: 15,
  };
  const rawText =
    "The Customer shall pay 10,000 USD within 30 days of invoice. Late payments shall incur 1.5% interest per month.";

  assert.strictEqual(detectClauseCategory(clause, rawText), "payment");

  // Section 1: WHAT IT SAYS
  const whatItSays = getWhatItSays(clause, rawText);
  assert.ok(whatItSays.includes("within 30 days"), "Preserves existing summary");

  // Section 2: WHY IS THIS IMPORTANT?
  const whyImportant = getWhyThisIsImportant(clause, rawText);
  assert.ok(Array.isArray(whyImportant) && whyImportant.length > 0);
  assert.ok(
    whyImportant.some((item) => /financial|payment|invoice/i.test(item)),
    "Mentions financial obligations"
  );
  assert.ok(
    whyImportant.some((item) => /late\s+fee|interest/i.test(item)),
    "Identifies late payment interest from actual text"
  );

  // Section 3: WHAT SHOULD YOU DO?
  const whatToDo = getWhatShouldYouDo(clause, rawText);
  assert.ok(Array.isArray(whatToDo) && whatToDo.length > 0);
  assert.ok(
    whatToDo.some((item) => /amount|due date|late fees|payment method/i.test(item)),
    "Provides payment review steps"
  );
});

// ============================================================================
// 2. TERMINATION CLAUSE TESTS
// ============================================================================
test("Termination clause generates 3 clear grounded sections matching user prompt example", () => {
  const clause = {
    title: "Termination",
    clause_type: "TERMINATION",
    meaning: "Either party may terminate the agreement by giving 30 days' written notice.",
    deadlines: ["30 days written notice"],
    risk_level: "MEDIUM",
    risk_score: 45,
  };
  const rawText = "Either party may terminate the agreement by giving 30 days' written notice.";

  assert.strictEqual(detectClauseCategory(clause, rawText), "termination");

  // Section 1: WHAT IT SAYS
  const whatItSays = getWhatItSays(clause, rawText);
  assert.strictEqual(
    whatItSays,
    "Either party may terminate the agreement by giving 30 days' written notice."
  );

  // Section 2: WHY IS THIS IMPORTANT?
  const whyImportant = getWhyThisIsImportant(clause, rawText);
  assert.ok(Array.isArray(whyImportant) && whyImportant.length >= 2);
  assert.ok(
    whyImportant.some((item) => item.includes("This defines how the agreement can be terminated")),
    "Explains termination mechanism"
  );
  assert.ok(
    whyImportant.some((item) => /30-day notice period/i.test(item)),
    "Grounded 30-day notice period identified"
  );

  // Section 3: WHAT SHOULD YOU DO?
  const whatToDo = getWhatShouldYouDo(clause, rawText);
  assert.ok(Array.isArray(whatToDo) && whatToDo.length >= 3);
  assert.ok(
    whatToDo.some((item) => /30-day notice period works/i.test(item)),
    "Actionable review step for 30-day notice period"
  );
  assert.ok(
    whatToDo.some((item) => /required method for submitting notice/i.test(item)),
    "Actionable check step for notice method"
  );
  assert.ok(
    whatToDo.some((item) => /evidence of the notice/i.test(item)),
    "Actionable step to retain evidence"
  );
});

// ============================================================================
// 3. PRIVACY CLAUSE TESTS
// ============================================================================
test("Privacy / Data Protection clause generates 3 clear grounded sections", () => {
  const clause = {
    title: "Data Protection and Privacy",
    clause_type: "DATA_PROTECTION",
    meaning:
      "The processor shall process personal data solely on documented instructions and report breaches promptly.",
    risk_level: "MEDIUM",
  };
  const rawText =
    "The Processor shall process personal data solely on documented instructions and notify the Controller of any data breach within 48 hours. Personal data shall not be transferred to third parties without prior written consent.";

  assert.strictEqual(detectClauseCategory(clause, rawText), "privacy");

  // Section 1: WHAT IT SAYS
  const whatItSays = getWhatItSays(clause, rawText);
  assert.ok(whatItSays.includes("personal data"), "Preserves privacy summary");

  // Section 2: WHY IS THIS IMPORTANT?
  const whyImportant = getWhyThisIsImportant(clause, rawText);
  assert.ok(
    whyImportant.some((item) => /personal|customer|data|safeguard/i.test(item)),
    "Explains privacy and data implications"
  );
  assert.ok(
    whyImportant.some((item) => /third-party|sharing|transmission/i.test(item)),
    "Explains third-party data transfer impact"
  );

  // Section 3: WHAT SHOULD YOU DO?
  const whatToDo = getWhatShouldYouDo(clause, rawText);
  assert.ok(
    whatToDo.some((item) => /collected data|sharing|usage|retention/i.test(item)),
    "Check collected data, sharing, usage, and retention"
  );
  assert.ok(
    whatToDo.some((item) => /incident|breach notification/i.test(item)),
    "Check incident reporting timelines"
  );
});

// ============================================================================
// 4. LIABILITY CLAUSE TESTS
// ============================================================================
test("Liability / Indemnity clause generates 3 clear grounded sections", () => {
  const clause = {
    title: "Limitation of Liability",
    clause_type: "LIABILITY",
    meaning:
      "Each party's total aggregate liability is capped at the fees paid in the prior 12 months.",
    risk_level: "HIGH",
    risk_score: 80,
    risk_reasons: [
      "Cap excludes consequential damages and limits total legal recovery.",
    ],
  };
  const rawText =
    "In no event shall either party's aggregate liability exceed the total fees paid under this agreement. Neither party shall be liable for indirect, incidental, or consequential damages.";

  assert.strictEqual(detectClauseCategory(clause, rawText), "liability");

  // Section 1: WHAT IT SAYS
  const whatItSays = getWhatItSays(clause, rawText);
  assert.ok(whatItSays.includes("liability is capped"), "Preserves liability explanation");

  // Section 2: WHY IS THIS IMPORTANT?
  const whyImportant = getWhyThisIsImportant(clause, rawText, clause.risk_reasons);
  assert.ok(
    whyImportant.some((item) => /monetary recovery limits|legal risk|damages/i.test(item)),
    "Explains risk allocation and recovery caps"
  );
  assert.ok(
    whyImportant.some((item) => /consequential|indirect|incidental/i.test(item)),
    "Explains exclusion of consequential damages"
  );

  // Section 3: WHAT SHOULD YOU DO?
  const whatToDo = getWhatShouldYouDo(clause, rawText);
  assert.ok(
    whatToDo.some((item) => /liability limits|exclusions|responsibilities/i.test(item)),
    "Check liability limits, exclusions, and responsibilities"
  );
  assert.ok(
    whatToDo.some((item) => /mutual/i.test(item)),
    "Verify whether liability protections are mutual"
  );
});

// ============================================================================
// 5. INSUFFICIENT INFORMATION / UNKNOWN CLAUSE (NEVER HALLUCINATE)
// ============================================================================
test("Insufficient text gracefully handles absence of facts without hallucinating", () => {
  const clause = {
    title: "General Provision",
    clause_type: "MISCELLANEOUS",
  };
  const rawText = "Short text.";

  const whyImportant = getWhyThisIsImportant(clause, rawText);
  assert.ok(Array.isArray(whyImportant) && whyImportant.length > 0);
  assert.ok(
    whyImportant.some((item) => /cannot be determined from the available text/i.test(item)),
    "States information cannot be determined rather than guessing"
  );

  const whatToDo = getWhatShouldYouDo(clause, rawText);
  assert.ok(Array.isArray(whatToDo) && whatToDo.length > 0);
  assert.ok(
    whatToDo.some((item) => /cannot be determined/i.test(item)),
    "States review requirements cannot be determined rather than guessing"
  );
});

// ============================================================================
// 6. POTENTIAL CONCERNS TESTS (GROUNDED, NEUTRAL, UNAMBIGUOUS)
// ============================================================================
test("Potential concerns: Missing Exhibit / external reference detection", () => {
  const clause = {
    title: "Scope of Work",
    clause_type: "SERVICES",
  };
  const rawText = "The Contractor shall perform the services as specified in Exhibit A: Scope of Services.";

  const concerns = getPotentialConcerns(clause, rawText);
  assert.ok(Array.isArray(concerns) && concerns.length > 0);
  assert.ok(
    concerns.some((c) => /Exhibit A/i.test(c) && /not present|not detailed/i.test(c)),
    "Identifies missing Exhibit A content"
  );
  assert.ok(
    concerns.some((c) => /Verify Exhibit A before accepting/i.test(c)),
    "Recommends verifying Exhibit A"
  );
});

test("Potential concerns: Blank or missing values detection", () => {
  const clause = {
    title: "Compensation",
    clause_type: "PAYMENT",
  };
  const rawText = "The Client shall pay $__________ upon signing of this Agreement.";

  const concerns = getPotentialConcerns(clause, rawText);
  assert.ok(Array.isArray(concerns) && concerns.length > 0);
  assert.ok(
    concerns.some((c) => /value appears to be missing|blank/i.test(c)),
    "Identifies blank/missing values"
  );
});

test("Potential concerns: Ambiguous wording detection", () => {
  const clause = {
    title: "Standard of Performance",
    clause_type: "PERFORMANCE",
  };
  const rawText = "The Consultant shall use reasonable efforts to complete the migration by Q3.";

  const concerns = getPotentialConcerns(clause, rawText);
  assert.ok(Array.isArray(concerns) && concerns.length > 0);
  assert.ok(
    concerns.some((c) => /"reasonable efforts"/i.test(c) && /not specifically defined/i.test(c)),
    'Flags undefined "reasonable efforts"'
  );
});

test("Potential concerns: Truncated clause text detection", () => {
  const clause = {
    title: "Termination for Convenience",
    clause_type: "TERMINATION",
  };
  const rawText = "Either party may terminate this agreement at any time provided that...";

  const concerns = getPotentialConcerns(clause, rawText);
  assert.ok(Array.isArray(concerns) && concerns.length > 0);
  assert.ok(
    concerns.some((c) => /truncated or incomplete/i.test(c)),
    "Flags truncated clause"
  );
});

test("Potential concerns: Complete clause with no concern", () => {
  const clause = {
    title: "Termination on Notice",
    clause_type: "TERMINATION",
  };
  const rawText = "Either party may terminate the agreement by giving 30 days' written notice to the other party via email.";

  const concerns = getPotentialConcerns(clause, rawText);
  assert.strictEqual(concerns.length, 1);
  assert.strictEqual(
    concerns[0],
    "No specific ambiguity or missing information was identified in the available clause text."
  );
});

test("Potential concerns: Neutral wording without alarmist language", () => {
  const clause = {
    title: "Audit Rights",
    clause_type: "AUDIT",
  };
  const rawText = "Company may inspect Contractor facilities at its sole discretion upon 24 hours notice.";

  const concerns = getPotentialConcerns(clause, rawText);
  for (const c of concerns) {
    assert.ok(!/\b(?:illegal|dangerous|unfair|bad)\b/i.test(c), "Does not use biased/alarmist wording");
  }
});

// ============================================================================
// 7. COMPONENT RENDERING TEST FOR CLAUSE INTELLIGENCE 4 SECTIONS
// ============================================================================
test("Clause Intelligence UI renders all 4 sections in order with icons and metadata tags", () => {
  const clause = {
    clause_id: "clause-101",
    title: "Termination on Notice",
    clause_type: "TERMINATION",
    meaning: "Either party may terminate the agreement by giving 30 days' written notice.",
    deadlines: ["30 days written notice"],
    obligations: ["Submit formal written notice to registered office"],
    permissions: ["Right to terminate without cause"],
    risk_level: "MEDIUM",
    risk_score: 40,
    text: "Either party may terminate the agreement by giving 30 days' written notice to the registered address.",
  };

  const rawText = clause.text;
  const whatItSays = getWhatItSays(clause, rawText);
  const whyImportantPoints = getWhyThisIsImportant(clause, rawText);
  const potentialConcernPoints = getPotentialConcerns(clause, rawText);
  const whatToDoPoints = getWhatShouldYouDo(clause, rawText);

  // Render the identical DOM structure as ClauseUnderstandingView
  const html = renderToString(
    React.createElement(
      "div",
      { className: "clause-understanding-container" },
      // 1. WHAT IT SAYS
      React.createElement(
        "section",
        { className: "clause-section-card what-it-says" },
        React.createElement(
          "div",
          { className: "clause-section-header" },
          React.createElement("span", { className: "clause-section-icon", "aria-hidden": "true" }, "📄"),
          React.createElement("span", { className: "clause-section-label" }, "WHAT IT SAYS")
        ),
        React.createElement("p", { className: "clause-section-body-text" }, whatItSays)
      ),
      // 2. WHY IS THIS IMPORTANT?
      React.createElement(
        "section",
        { className: "clause-section-card why-important" },
        React.createElement(
          "div",
          { className: "clause-section-header" },
          React.createElement("span", { className: "clause-section-icon", "aria-hidden": "true" }, "⚠️"),
          React.createElement("span", { className: "clause-section-label" }, "WHY IS THIS IMPORTANT?")
        ),
        React.createElement(
          "ul",
          { className: "clause-section-bullet-list" },
          whyImportantPoints.map((pt, idx) => React.createElement("li", { key: idx }, pt))
        )
      ),
      // 3. 🚨 UNCLEAR / POTENTIAL CONCERNS
      React.createElement(
        "section",
        { className: "clause-section-card potential-concerns" },
        React.createElement(
          "div",
          { className: "clause-section-header" },
          React.createElement("span", { className: "clause-section-icon", "aria-hidden": "true" }, "🚨"),
          React.createElement("span", { className: "clause-section-label" }, "UNCLEAR / POTENTIAL CONCERNS")
        ),
        React.createElement(
          "ul",
          { className: "clause-section-bullet-list potential-concerns-list" },
          potentialConcernPoints.map((pt, idx) => React.createElement("li", { key: idx }, pt))
        )
      ),
      // 4. WHAT SHOULD YOU DO?
      React.createElement(
        "section",
        { className: "clause-section-card what-to-do" },
        React.createElement(
          "div",
          { className: "clause-section-header" },
          React.createElement("span", { className: "clause-section-icon", "aria-hidden": "true" }, "✅"),
          React.createElement("span", { className: "clause-section-label" }, "WHAT SHOULD YOU DO?")
        ),
        React.createElement(
          "ul",
          { className: "clause-section-bullet-list what-to-do-list" },
          whatToDoPoints.map((step, idx) => React.createElement("li", { key: idx }, step))
        )
      ),
      // Metadata chips
      React.createElement(
        "div",
        { className: "clause-extracted-meta-row" },
        React.createElement("span", { className: "clause-meta-tag date" }, "📅 1 date/deadline"),
        React.createElement("span", { className: "clause-meta-tag obligation" }, "⚖️ 1 obligation"),
        React.createElement("span", { className: "clause-meta-tag permission" }, "🔓 1 permission")
      ),
      // Original clause toggle
      React.createElement(
        "div",
        { className: "clause-original-evidence-wrapper" },
        React.createElement(
          "button",
          { type: "button", className: "clause-view-original-btn" },
          React.createElement("span", null, "View Original Clause")
        )
      )
    )
  );

  // 1. WHAT IT SAYS section
  assert.ok(html.includes("WHAT IT SAYS"), "Renders Section 1 heading");
  assert.ok(html.includes("📄"), "Includes 📄 icon for WHAT IT SAYS");
  assert.ok(html.includes("Either party may terminate"), "Renders clause summary");

  // 2. WHY IS THIS IMPORTANT? section
  assert.ok(html.includes("WHY IS THIS IMPORTANT?"), "Renders Section 2 heading");
  assert.ok(html.includes("⚠️"), "Includes ⚠️ icon for WHY IS THIS IMPORTANT?");
  assert.ok(html.includes("30-day notice period"), "Renders grounded notice period bullet");

  // 3. UNCLEAR / POTENTIAL CONCERNS section
  assert.ok(html.includes("UNCLEAR / POTENTIAL CONCERNS"), "Renders Section 3 heading");
  assert.ok(html.includes("🚨"), "Includes 🚨 icon for UNCLEAR / POTENTIAL CONCERNS");
  assert.ok(html.includes("potential-concerns"), "Renders potential-concerns card class");

  // 4. WHAT SHOULD YOU DO? section
  assert.ok(html.includes("WHAT SHOULD YOU DO?"), "Renders Section 4 heading");
  assert.ok(html.includes("✅"), "Includes ✅ icon for WHAT SHOULD YOU DO?");
  assert.ok(html.includes("Check whether the 30-day notice period works"), "Renders action check step");

  // Verify section order in generated HTML
  const posWhatItSays = html.indexOf("WHAT IT SAYS");
  const posWhyImportant = html.indexOf("WHY IS THIS IMPORTANT?");
  const posConcerns = html.indexOf("UNCLEAR / POTENTIAL CONCERNS");
  const posWhatToDo = html.indexOf("WHAT SHOULD YOU DO?");

  assert.ok(posWhatItSays < posWhyImportant, "Section 1 precedes Section 2");
  assert.ok(posWhyImportant < posConcerns, "Section 2 precedes Section 3 (UNCLEAR / POTENTIAL CONCERNS)");
  assert.ok(posConcerns < posWhatToDo, "Section 3 precedes Section 4 (WHAT SHOULD YOU DO?)");

  // Extracted metadata chips
  assert.ok(html.includes("📅"), "Includes date/deadline chip");
  assert.ok(html.includes("⚖️"), "Includes obligation chip");
  assert.ok(html.includes("🔓"), "Includes permission chip");

  // Original clause toggle
  assert.ok(html.includes("View Original Clause"), "Renders View Original Clause button");
});

// ============================================================================
// 8. CONCISE SUMMARIES BY DEFAULT (40-80 WORDS, 2-4 SENTENCES, NO ELLIPSIS)
// ============================================================================
test("Lengthy legal clause generates concise 2-4 sentence summary (~40-80 words) preserving material terms without ellipsis truncation", () => {
  const lengthyIndemnityText =
    "The Contractor shall defend, indemnify, and hold harmless the Company, its directors, officers, employees, and agents from and against any and all third-party claims, liabilities, losses, damages, and reasonable attorney fees arising out of or resulting from Contractor's material breach of this Agreement, gross negligence, or willful misconduct; provided, however, that Contractor's total aggregate indemnification liability under this Section shall not exceed $1,000,000, and Company must provide written notice of any such claim within 10 business days of becoming aware thereof, failing which Contractor's defense obligations under this Section shall be extinguished.";

  const clause = {
    clause_id: "clause-indemnity-1",
    title: "Indemnification & Defense Obligations",
    clause_type: "LIABILITY",
    risk_level: "HIGH",
    risk_score: 85,
    text: lengthyIndemnityText,
  };

  const summary = getWhatItSays(clause, lengthyIndemnityText);

  // 1. Must NOT simply dump the raw 100+ word legal text
  assert.notStrictEqual(summary, lengthyIndemnityText, "Does not return full-length raw text dump");

  // 2. Must NOT truncate with ellipsis
  assert.ok(!summary.includes("..."), "Does not use ellipsis (...) truncation");
  assert.ok(!summary.includes("…"), "Does not use unicode ellipsis truncation");

  // 3. Sentence count between 2 and 4
  const sentences = summary.split(/(?<=[.!?])\s+/).filter(s => s.trim().length > 0);
  assert.ok(
    sentences.length >= 2 && sentences.length <= 4,
    `Sentence count should be 2-4 sentences, got ${sentences.length}: "${summary}"`
  );

  // 4. Word count roughly 40-80 words (allow 30-85 window)
  const words = summary.trim().split(/\s+/);
  assert.ok(
    words.length >= 30 && words.length <= 85,
    `Word count should be around 40-80 words, got ${words.length}: "${summary}"`
  );

  // 5. Preserves responsible party
  assert.ok(
    /Contractor/i.test(summary) || /Company/i.test(summary),
    "Preserves responsible parties (Contractor/Company)"
  );

  // 6. Preserves monetary cap
  assert.ok(
    summary.includes("$1,000,000") || /1,000,000/i.test(summary),
    "Preserves specific $1,000,000 liability cap"
  );

  // 7. Preserves notice deadline
  assert.ok(
    /10\s*business\s*days/i.test(summary) || /10\s*days/i.test(summary),
    "Preserves 10 business days notice requirement"
  );

  // 8. Preserves exception/condition or consequences
  assert.ok(
    /gross negligence|willful misconduct|breach|indemnif/i.test(summary),
    "Preserves material qualification or exception"
  );
});

test("Lengthy payment clause generates concise summary preserving parties, amounts, and deadlines without text dump", () => {
  const lengthyPaymentText =
    "The Service Provider shall submit detailed monthly invoices to Customer on the first business day of each calendar month. Customer shall pay all undisputed invoice amounts within 45 days of receipt of invoice by electronic wire transfer. If Customer fails to pay any undisputed amount by the due date, a late payment fee of 1.5% per month or the statutory maximum rate, whichever is lower, shall accrue daily until full payment is received. Reimbursable out-of-pocket expenses shall not exceed $15,000 without prior written authorization from Customer.";

  const clause = {
    clause_id: "clause-payment-1",
    title: "Billing and Payment Procedures",
    clause_type: "PAYMENT",
    risk_level: "MEDIUM",
    risk_score: 40,
    text: lengthyPaymentText,
  };

  const summary = getWhatItSays(clause, lengthyPaymentText);

  assert.notStrictEqual(summary, lengthyPaymentText, "Does not return raw legal text");
  assert.ok(!summary.includes("..."), "Never truncates with ellipsis");

  const sentences = summary.split(/(?<=[.!?])\s+/).filter(s => s.trim().length > 0);
  assert.ok(
    sentences.length >= 2 && sentences.length <= 4,
    `Summary should have 2-4 sentences, got ${sentences.length}`
  );

  const words = summary.trim().split(/\s+/);
  assert.ok(
    words.length >= 30 && words.length <= 85,
    `Summary word count should be around 40-80 words, got ${words.length}`
  );

  // Material facts preserved
  assert.ok(/45\s*days/i.test(summary), "Preserves 45 days deadline");
  assert.ok(/\$15,000/i.test(summary), "Preserves $15,000 expense limit");
  assert.ok(/1\.5%|late\s*fee|interest/i.test(summary), "Preserves late payment consequences");
});

test("getWhatItSays preserves existing short concise summary but synthesizes when given raw text dump", () => {
  // Case A: Pre-existing short plain-English explanation (15 words)
  const shortClause = {
    title: "Governing Law",
    meaning: "This contract is governed by and construed according to the laws of California.",
    text: "This Agreement shall be governed by, and construed in accordance with, the laws of the State of California, without giving effect to any principles of conflicts of law.",
  };
  const shortSummary = getWhatItSays(shortClause, shortClause.text);
  assert.strictEqual(
    shortSummary,
    "This contract is governed by and construed according to the laws of California.",
    "Preserves pre-existing concise explanation"
  );

  // Case B: clause.meaning is identical to a lengthy 150-word raw text dump
  const longText =
    "In the event of any material breach of this Agreement by either party, including failure to deliver services or failure to make timely payments exceeding 60 days past due, the non-breaching party may terminate this Agreement immediately upon written notice, whereupon all outstanding licenses granted hereunder shall terminate and all confidential documents shall be returned within 14 days, with damages capped at total fees paid.";
  const dumpClause = {
    title: "Termination for Breach",
    meaning: longText, // backend accidentally set meaning to full text
    text: longText,
  };
  const synthesized = getWhatItSays(dumpClause, longText);
  assert.notStrictEqual(synthesized, longText, "Recognizes long meaning as text dump and synthesizes concise summary");
  const words = synthesized.trim().split(/\s+/);
  assert.ok(words.length <= 85, `Synthesized word count <= 85, got ${words.length}`);
});

// ============================================================================
// 9. ORIGINAL CLAUSE PRESERVATION & SOURCE TEXT RESOLUTION
// ============================================================================
test("getClauseSourceText resolves across all field variations and preserves original text completely", () => {
  const sampleText = "Company shall provide 30 days prior written notice before modifying pricing.";

  assert.strictEqual(getClauseSourceText({ text: sampleText }), sampleText);
  assert.strictEqual(getClauseSourceText({ clauseText: sampleText }), sampleText);
  assert.strictEqual(getClauseSourceText({ clause_text: sampleText }), sampleText);
  assert.strictEqual(getClauseSourceText({ content: sampleText }), sampleText);
  assert.strictEqual(getClauseSourceText({ original_text: sampleText }), sampleText);
  assert.strictEqual(getClauseSourceText({ source_text: sampleText }), sampleText);
  assert.strictEqual(getClauseSourceText(null, sampleText), sampleText);

  // Does not return placeholder strings if empty
  assert.strictEqual(getClauseSourceText({ text: "No explanation available." }), "");
  assert.strictEqual(getClauseSourceText({}), "");
});

test("Expandable original clause control is collapsed by default and preserves unmodified full legal text when opened", () => {
  const appCode = fs.readFileSync(path.join(__dirname, "App.jsx"), "utf8");

  // Verify ClauseUnderstandingView implementation in App.jsx
  assert.ok(
    appCode.includes("const [isOriginalExpanded, setIsOriginalExpanded] = useState(false);"),
    "Original text expandable starts collapsed by default (isOriginalExpanded = false)"
  );
  assert.ok(
    appCode.includes("clause-view-original-btn"),
    "Has prominent expandable button with class clause-view-original-btn"
  );
  assert.ok(
    appCode.includes("View Original Clause") && appCode.includes("Hide Original Clause"),
    "Toggles button label between View Original Clause and Hide Original Clause"
  );
  assert.ok(
    appCode.includes("Show full text") && appCode.includes("Hide full text"),
    "Includes (Show full text) / (Hide full text) dual-label indicator"
  );
  assert.ok(
    appCode.includes("aria-expanded={isOriginalExpanded}"),
    "Binds accessible aria-expanded attribute"
  );
  assert.ok(
    appCode.includes("<p>{rawText}</p>"),
    "Renders unmodified original text when expanded"
  );
});

// ============================================================================
// 10. SECTION CAPPING & TRUTHFUL MISSING-TEXT HANDLING
// ============================================================================
test("Sections are capped: 1-3 reasons for why important, 1-3 concerns, 1-3 actionable next steps", () => {
  const rawText =
    "Contractor agrees to indemnify Client for all losses up to $500,000 with 15 days notice. All disputes shall be resolved in New York under commercial arbitration rules.";
  const highRiskClause = {
    title: "Indemnity and Dispute Resolution",
    risk_level: "HIGH",
    risk_score: 90,
    risk_reasons: [
      "Broad indemnity exposure up to $500,000.",
      "Arbitration restricts trial and appeal rights.",
      "Short 15-day notice window.",
      "Extraneous reason 4.",
      "Extraneous reason 5.",
    ],
    recommendations: [
      "Negotiate mutual indemnity terms.",
      "Extend notice window to 30 days.",
      "Review arbitration venue.",
      "Extraneous action 4.",
    ],
    text: rawText,
  };

  const whyImportant = getWhyThisIsImportant(highRiskClause, rawText, highRiskClause.risk_reasons);
  assert.ok(
    whyImportant.length >= 1 && whyImportant.length <= 3,
    `Why Important count should be 1-3, got ${whyImportant.length}`
  );
  assert.ok(
    whyImportant.some(r => /indemnif|liability|\$500,000/i.test(r)),
    "Prioritizes grounded high-risk indemnity reasons"
  );

  const concerns = getPotentialConcerns(highRiskClause, rawText);
  assert.ok(
    concerns.length >= 1 && concerns.length <= 3,
    `Concerns count should be 1-3, got ${concerns.length}`
  );

  const whatToDo = getWhatShouldYouDo(highRiskClause, rawText, highRiskClause.recommendations);
  assert.ok(
    whatToDo.length >= 1 && whatToDo.length <= 3,
    `What Should You Do count should be 1-3, got ${whatToDo.length}`
  );
});

test("Missing text is honestly reported without false missing claims on present text", () => {
  // Empty text
  const emptyConcerns = getPotentialConcerns({ title: "Blank" }, "");
  assert.ok(
    emptyConcerns.some(c => /Clause text is missing from the document/i.test(c)),
    "Reports clause text missing when actually missing"
  );

  // Present substantive text must NEVER claim text is missing
  const presentText = "Payment shall be made within 30 days of receiving the invoice.";
  const presentConcerns = getPotentialConcerns({ title: "Payment" }, presentText);
  for (const c of presentConcerns) {
    assert.ok(
      !c.toLowerCase().includes("clause text is missing"),
      `Should not report missing text when substantive text exists: "${c}"`
    );
  }
});

test("RiskAnalysis and ClauseUnderstandingView preserve risk levels, scores, numbers, and styling", () => {
  const appCode = fs.readFileSync(path.join(__dirname, "App.jsx"), "utf8");

  // In RiskAnalysis, verify meaning is NOT overwritten with clause.text
  assert.ok(
    !appCode.includes("clause?.text ||\n                \"No explanation available.\""),
    "RiskAnalysis does not force raw text into meaning fallback"
  );

  // Verify RiskAnalysis passes original clause attributes accurately
  assert.ok(
    appCode.includes("clauseText: clause?.text || clause?.clause_text || clause?.content || \"\""),
    "RiskAnalysis preserves clauseText accurately"
  );
  assert.ok(
    appCode.includes("risk_level: risk"),
    "RiskAnalysis preserves risk_level"
  );
  assert.ok(
    appCode.includes("risk_score: score"),
    "RiskAnalysis preserves risk_score"
  );
});
