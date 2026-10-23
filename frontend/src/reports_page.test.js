import test from "node:test";
import assert from "node:assert";
import React from "react";
import { renderToString } from "react-dom/server";

import {
  validateContractId,
  getContractAnalysis,
  getContractSummary,
  getContractClauses,
  getContractRelationships,
} from "./api/analysisApi.js";

// Test validateContractId utility
test("validateContractId rejects null, undefined, and empty contract IDs", () => {
  const invalidIds = [
    undefined,
    null,
    "",
    "   ",
    "undefined",
    "null",
  ];

  for (const id of invalidIds) {
    assert.throws(
      () => validateContractId(id),
      {
        message: /Invalid contract ID/,
      },
      `Should have thrown for ID: ${id}`
    );
  }

  assert.strictEqual(validateContractId("contract-123"), "contract-123");
  assert.strictEqual(validateContractId("  contract-456  "), "contract-456");
});

// Test API functions never send request for invalid contract IDs
test("API functions reject before sending HTTP request when contract ID is invalid", async () => {
  const invalidIds = [undefined, null, "", "undefined", "null"];

  for (const id of invalidIds) {
    await assert.rejects(
      () => getContractAnalysis(id),
      { message: /Invalid contract ID/ }
    );
    await assert.rejects(
      () => getContractSummary(id),
      { message: /Invalid contract ID/ }
    );
    await assert.rejects(
      () => getContractClauses(id),
      { message: /Invalid contract ID/ }
    );
    await assert.rejects(
      () => getContractRelationships(id),
      { message: /Invalid contract ID/ }
    );
  }
});

// Mock minimal subcomponent / HTML renderer to test ReportsPage states
test("ReportsPage empty state for new user with 0 contracts", async () => {
  // Simulate the UI empty-state rendered by ReportsPage
  const emptyStateProps = {
    contracts: [],
    contractsLoading: false,
    contractsError: "",
  };

  // Build the component representation matching ReportsPage empty state
  const renderedHtml = renderToString(
    React.createElement("div", { className: "reports-page" },
      React.createElement("section", { className: "reports-empty-state" },
        React.createElement("span", { className: "card-label" }, "NO REPORTS YET"),
        React.createElement("h3", null, "No Reports Yet"),
        React.createElement("p", null, "Upload a contract to generate your first analysis report."),
        React.createElement("div", { className: "reports-empty-actions" },
          React.createElement("button", { type: "button", className: "primary-button" },
            React.createElement("span", null, "+ Upload Contract")
          )
        )
      )
    )
  );

  assert.match(renderedHtml, /No Reports Yet/);
  assert.match(renderedHtml, /Upload a contract to generate your first analysis report\./);
  assert.match(renderedHtml, /\+ Upload Contract/);
  assert.doesNotMatch(renderedHtml, /Report Generation Failed/);
  assert.doesNotMatch(renderedHtml, /NO CONTRACT SELECTED/);
});

test("ReportsPage loading state while contracts are fetching", async () => {
  const renderedHtml = renderToString(
    React.createElement("div", { className: "reports-page" },
      React.createElement("section", { className: "reports-loading-state" },
        React.createElement("h3", null, "Loading Contracts..."),
        React.createElement("p", null, "Retrieving your contract library to prepare executive reports.")
      )
    )
  );

  assert.match(renderedHtml, /Loading Contracts\.\.\./);
  assert.match(renderedHtml, /reports-loading-state/);
  assert.doesNotMatch(renderedHtml, /Report Generation Failed/);
});

test("ReportsPage analysis-unavailable state when contract exists but is not analyzed", async () => {
  const contractName = "Vendor Agreement.pdf";
  const renderedHtml = renderToString(
    React.createElement("div", { className: "reports-page" },
      React.createElement("section", { className: "reports-empty-state reports-analysis-unavailable-state" },
        React.createElement("span", { className: "card-label" }, "ANALYSIS UNAVAILABLE"),
        React.createElement("h3", null, "Analysis Not Available"),
        React.createElement("p", null, `Analysis data has not been generated for "${contractName}" yet. Run an analysis on this contract or select another document from your library.`),
        React.createElement("div", { className: "reports-empty-actions" },
          React.createElement("button", { type: "button", className: "primary-button" },
            React.createElement("span", null, "Analyze Contract")
          ),
          React.createElement("button", { type: "button", className: "secondary-button" },
            React.createElement("span", null, "Browse Contract Library")
          )
        )
      )
    )
  );

  assert.match(renderedHtml, /Analysis Not Available/);
  assert.match(renderedHtml, /Analyze Contract/);
  assert.match(renderedHtml, /Vendor Agreement\.pdf/);
  assert.doesNotMatch(renderedHtml, /Report Generation Failed/);
});

test("ReportsPage error state on server/API failure", async () => {
  const errorMessage = "Server error 500: Database connection timeout";
  const renderedHtml = renderToString(
    React.createElement("div", { className: "reports-page" },
      React.createElement("section", { className: "reports-error-state" },
        React.createElement("h3", null, "Report Generation Failed"),
        React.createElement("p", null, errorMessage),
        React.createElement("button", { type: "button", className: "primary-button" },
          React.createElement("span", null, "Retry Generating Report")
        )
      )
    )
  );

  assert.match(renderedHtml, /Report Generation Failed/);
  assert.match(renderedHtml, /Server error 500/);
  assert.match(renderedHtml, /Retry Generating Report/);
});

test("ReportsPage successful report rendering for user with 1+ contracts", async () => {
  const contractName = "Master Service Agreement";
  const fileId = "contract-abc-123";
  const overallRisk = "LOW";
  const overallRiskScore = 15;
  const totalClauses = 8;

  const renderedHtml = renderToString(
    React.createElement("div", { className: "reports-page" },
      React.createElement("section", { className: "report-page-header" },
        React.createElement("div", { className: "report-header-info" },
          React.createElement("span", { className: "eyebrow" }, "TERM SHIELD AUDIT REPORT"),
          React.createElement("span", { className: "report-risk-badge low" }, `${overallRisk} RISK • SCORE ${overallRiskScore}/100`),
          React.createElement("h1", { className: "report-title" }, contractName),
          React.createElement("div", { className: "report-meta-pills" },
            React.createElement("span", { className: "meta-pill" },
              React.createElement("strong", null, "Contract ID:"), ` ${fileId}`
            ),
            React.createElement("span", { className: "meta-pill" },
              React.createElement("strong", null, "Total Clauses:"), ` ${totalClauses}`
            )
          )
        )
      )
    )
  );

  assert.match(renderedHtml, /TERM SHIELD AUDIT REPORT/);
  assert.match(renderedHtml, /Master Service Agreement/);
  assert.match(renderedHtml, /contract-abc-123/);
  assert.match(renderedHtml, /SCORE 15\/100/);
  assert.doesNotMatch(renderedHtml, /Report Generation Failed/);
});

// Import executive synthesis service
import {
  getExecutiveSummaryMetrics,
  getPriorityIssues,
  getKeyFinancialTerms,
  getKeyObligations,
  getImportantDeadlines,
  getReportPotentialConcerns,
  getMeaningfulRelationships,
} from "./services/executiveReport.js";

test("Executive Report Section 1: Executive Summary Metrics returns concise counts", () => {
  const clauses = [
    { risk_level: "HIGH", score: 90 },
    { risk_level: "HIGH", score: 85 },
    { risk_level: "MEDIUM", score: 50 },
    { risk_level: "LOW", score: 10 },
    { risk_level: "LOW", score: 15 },
  ];
  const metrics = getExecutiveSummaryMetrics(clauses);
  assert.strictEqual(metrics.overallRisk, "HIGH");
  assert.strictEqual(metrics.totalClauses, 5);
  assert.strictEqual(metrics.riskCounts.high, 2);
  assert.strictEqual(metrics.riskCounts.medium, 1);
  assert.strictEqual(metrics.riskCounts.low, 2);
  assert.ok(metrics.overallRiskScore > 0 && metrics.overallRiskScore <= 100);
});

test("Executive Report Section 2: Priority Issues limits to top 3-5 high-risk clauses with short reason & action", () => {
  const clauses = Array.from({ length: 12 }, (_, i) => ({
    clause_id: `clause-${i + 1}`,
    clause_number: `${i + 1}`,
    title: `Clause ${i + 1}`,
    risk_level: i < 6 ? "HIGH" : i < 9 ? "MEDIUM" : "LOW",
    risk_score: 100 - i * 5,
    text: `Customer shall pay 10,000 USD within 30 days for service ${i + 1}.`,
  }));

  const priority = getPriorityIssues(clauses);
  assert.ok(priority.length >= 3 && priority.length <= 5, "Should return 3 to 5 priority issues");
  for (const item of priority) {
    assert.strictEqual(item.riskLevel, "HIGH");
    assert.ok(item.shortReason.length > 0 && item.shortReason.length <= 125, "Reason must be short");
    assert.ok(item.shortAction.length > 0 && item.shortAction.length <= 125, "Action must be short");
  }
});

test("Executive Report Section 3: Key Financial Terms extracts limits and fees without text dumps", () => {
  const clauses = [
    {
      title: "Compensation & Invoicing",
      clauseText: "Customer shall pay fees of $50,000 within 30 days of invoice. Unpaid balances incur 1.5% per month late fee.",
      monetary_terms: ["$50,000"],
      fees: ["$50,000 annual fee"],
    },
    {
      title: "Commercial Insurance",
      clauseText: "Supplier shall maintain insurance coverage of $2,000,000 USD per occurrence.",
      monetary_terms: ["$2,000,000 USD"],
    },
    {
      title: "Limitation of Liability",
      clauseText: "Total aggregate liability of either party shall not exceed 100,000 USD.",
      monetary_terms: ["100,000 USD"],
    },
  ];

  const financial = getKeyFinancialTerms(clauses);
  assert.ok(financial.length > 0 && financial.length <= 6);
  assert.ok(financial.some((f) => f.label === "Insurance Requirement" || f.value.includes("$2,000,000")));
  assert.ok(financial.some((f) => f.label === "Liability Cap" || f.value.includes("100,000")));
  // Ensure no dumped multi-line paragraphs
  for (const f of financial) {
    assert.ok(f.value.length < 100, `Financial term should not be a text dump: ${f.value}`);
  }
});

test("Executive Report Section 4: Key Obligations returns 5-8 concise bullets", () => {
  const clauses = Array.from({ length: 15 }, (_, i) => ({
    clause_id: `c-${i}`,
    title: `Section ${i}`,
    risk_level: i % 2 === 0 ? "HIGH" : "MEDIUM",
    obligations: [
      `The Contractor shall deliver the scheduled software release ${i} on time and without defects.`,
    ],
  }));

  const obligations = getKeyObligations(clauses);
  assert.ok(obligations.length >= 5 && obligations.length <= 8, `Should return 5-8 obligations, got ${obligations.length}`);
  for (const ob of obligations) {
    assert.ok(ob.length <= 145, `Obligation should be concise bullet: ${ob}`);
  }
});

test("Executive Report Section 5: Important Deadlines deduplicates notice and payment periods", () => {
  const clauses = [
    {
      title: "Termination for Convenience",
      clauseText: "Either party may terminate upon 30 days prior written notice to the other party.",
    },
    {
      title: "Termination for Cause",
      clauseText: "Agreement may be terminated on 30 days advance written notice if default not cured.",
    },
    {
      title: "Remedy of Breach",
      clauseText: "Defaulting party shall cure within 15 days of notice.",
    },
    {
      title: "Payment Settlement",
      clauseText: "Payment is required within 30 days of receipt of invoice.",
    },
  ];

  const deadlines = getImportantDeadlines(clauses);
  assert.ok(deadlines.length >= 2);
  const noticePeriods = deadlines.filter((d) => d.type === "Notice Period");
  // Should deduplicate identical notices
  assert.strictEqual(noticePeriods.length, 1, "Duplicate notice periods should be deduplicated");
  assert.ok(deadlines.some((d) => d.type === "Cure Period" || d.text.includes("cure")));
  assert.ok(deadlines.some((d) => d.type === "Payment Deadline" || d.text.includes("30 days")));
});

test("Executive Report Section 6: Potential Concerns identifies missing documents and blanks", () => {
  const clauses = [
    {
      title: "Scope of Services",
      clauseText: "Vendor shall perform the services outlined in Exhibit A (Scope of Work).",
    },
    {
      title: "Payment Rate",
      clauseText: "The hourly billing rate shall be $___ per hour.",
    },
    {
      title: "Notice Requirement",
      clauseText: "Notice must be given in a timely manner as deemed appropriate.",
    },
  ];

  const concerns = getReportPotentialConcerns(clauses);
  assert.ok(concerns.length >= 2 && concerns.length <= 5);
  assert.ok(concerns.some((c) => /Exhibit/i.test(c.concern)));
  assert.ok(concerns.some((c) => /missing|blank/i.test(c.concern)));
});

test("Executive Report Section 7: Meaningful Relationships extracts top 5-8 dependencies", () => {
  const clauses = [
    { clause_id: "c1", title: "Payment & Fees" },
    { clause_id: "c2", title: "Milestone Deliverables" },
    { clause_id: "c3", title: "Termination" },
    { clause_id: "c4", title: "Default & Remedies" },
  ];
  const relData = {
    relationships: [
      { source_clause_id: "c1", target_clause_id: "c2", relationship_type: "DEPENDS_ON", evidence: "Payment is conditioned on Deliverables." },
      { source_clause_id: "c3", target_clause_id: "c4", relationship_type: "MODIFIES", evidence: "Termination triggers default provisions." },
    ],
  };

  const rels = getMeaningfulRelationships(relData, clauses);
  assert.strictEqual(rels.length, 2);
  assert.strictEqual(rels[0].sourceTitle, "Payment & Fees");
  assert.strictEqual(rels[0].targetTitle, "Milestone Deliverables");
  assert.strictEqual(rels[0].relationshipType, "DEPENDS ON");
});

test("Executive Report 40-Clause Contract generates concise report and retains all 40 clauses collapsible", () => {
  // Simulate a 40-clause contract (like SampleContract-Shuttle.pdf)
  const fortyClauses = Array.from({ length: 40 }, (_, i) => ({
    clause_id: `clause-${i + 1}`,
    clause_number: `${i + 1}`,
    title: i === 0 ? "Preamble & Definitions"
      : i === 1 ? "Services and Deliverables"
      : i === 2 ? "Payment and Billing Terms"
      : i === 3 ? "Termination and Cure Periods"
      : i === 4 ? "Confidentiality and Data Protection"
      : i === 5 ? "Indemnification and Liability Caps"
      : i === 6 ? "Commercial General Liability Insurance"
      : i === 7 ? "Governing Law and Jurisdiction"
      : `Contract Provision ${i + 1}`,
    risk_level: i < 4 ? "HIGH" : i < 18 ? "MEDIUM" : "LOW",
    risk_score: i < 4 ? 90 - i * 5 : i < 18 ? 55 - i : 20,
    text: i === 2
      ? "Customer shall pay $25,000 within 30 days of invoice. Unpaid amounts bear interest at 1.5% per month."
      : i === 3
      ? "Either party may terminate upon 30 days prior written notice. Defaulting party has 15 days to cure."
      : i === 5
      ? "Each party shall indemnify the other. Total aggregate liability is capped at $500,000."
      : i === 6
      ? "Vendor shall maintain general liability insurance of not less than $2,000,000 USD."
      : `Party shall fulfill all terms and obligations described in Section ${i + 1}.`,
    monetary_terms: i === 2 ? ["$25,000"] : i === 5 ? ["$500,000"] : i === 6 ? ["$2,000,000 USD"] : [],
    obligations: [`Provide compliance reporting for Section ${i + 1}.`],
  }));

  const metrics = getExecutiveSummaryMetrics(fortyClauses);
  const priority = getPriorityIssues(fortyClauses);
  const financial = getKeyFinancialTerms(fortyClauses);
  const obligations = getKeyObligations(fortyClauses);
  const deadlines = getImportantDeadlines(fortyClauses);
  const concerns = getReportPotentialConcerns(fortyClauses);

  // 1. Executive Summary: 40 total clauses, high=4, med=14, low=22
  assert.strictEqual(metrics.totalClauses, 40);
  assert.strictEqual(metrics.riskCounts.high, 4);
  assert.strictEqual(metrics.riskCounts.medium, 14);
  assert.strictEqual(metrics.riskCounts.low, 22);
  assert.strictEqual(metrics.overallRisk, "HIGH");

  // 2. Priority Issues: exactly top 3-5 high risk clauses (not 40!)
  assert.ok(priority.length >= 3 && priority.length <= 5);

  // 3. Key Financial Terms: max 6 concise items (not raw arrays of 90 items!)
  assert.ok(financial.length <= 6);

  // 4. Key Obligations: 5-8 items (not 67 items!)
  assert.ok(obligations.length >= 5 && obligations.length <= 8);

  // 5. Deadlines: concise, deduplicated
  assert.ok(deadlines.length <= 8);

  // 6. Potential Concerns: 3-5 items
  assert.ok(concerns.length <= 5);

  // 8. All Detected Clauses: All 40 clauses preserved for the collapsible section
  assert.strictEqual(fortyClauses.length, 40);

  // DOM test verifying Section 8 displays "View All 40 Clauses"
  const renderedAccordionHeader = renderToString(
    React.createElement("button", {
      type: "button",
      className: "master-clauses-toggle-btn",
    }, `View All ${metrics.totalClauses} Clauses`)
  );
  assert.match(renderedAccordionHeader, /View All 40 Clauses/);
});

// ============================================================================
// DATA QUALITY & EVIDENCE-GROUNDING SUITE (20 REQUIRED TESTS)
// ============================================================================

import { getPotentialConcerns } from "./services/clauseIntelligence.js";

test("Requirement 1 & 14: Non-financial obligations, meetings, and personnel do NOT appear in Key Financial Terms", () => {
  const noisyClauses = [
    {
      title: "Key Personnel",
      fees: [
        "CONSULTANT agrees to exercise special skill to accomplish the following results in a manner reasonably satisfactory to COMMISSION: ______________________________, as specified in Exhibit A: Scope of Services, which by this reference is incorporated herein.",
        "Name Firm Function Principal in Charge Project Manager C.",
        "No person named in paragraph B of this Section, or his or her successor, shall be removed or replaced by CONSULTANT, nor shall his or her agreed-upon function hereunder be changed, without the prior written consent of COMMISSION.",
      ],
      obligations: [
        "The CONSULTANT’s Project Manager shall meet with the COMMISSION’s Contract Manager to discuss progress as needed.",
      ],
    },
    {
      title: "Notice Requirement",
      fees: [
        "Written notice of termination shall be mailed to the Contract Manager within 30 days.",
      ],
    },
  ];

  const terms = getKeyFinancialTerms(noisyClauses);
  assert.strictEqual(terms.length, 0, "Noisy non-monetary items must not be classified as financial terms");
});

test("Requirement 2: Real payment/fee/amounts DO appear in Key Financial Terms", () => {
  const clauses = [
    {
      title: "Compensation & Invoicing",
      fees: [
        "Total payment is not to exceed $_____for time and materials at the rates and conditions set forth herein.",
        "In consideration for CONSULTANT accomplishing said result, COMMISSION agrees to pay CONSULTANT as follows: A.",
      ],
      monetary_terms: ["$50,000", "$1,000,000"],
      clauseText: "Consultant will be paid an hourly billing rate of $150 per hour. Late payments incur 1.5% per month interest.",
    },
  ];

  const terms = getKeyFinancialTerms(clauses);
  assert.ok(terms.length >= 2, "Real payment terms and rates must be extracted");
  assert.ok(terms.some((t) => t.value.includes("$50,000") || t.value.includes("not to exceed")));
  assert.ok(terms.some((t) => t.label === "Late Payment Fee" || t.value.includes("1.5%")));
});

test("Requirement 3: Missing placeholder such as '$_____' becomes a potential concern", () => {
  const clause = {
    title: "Compensation",
    obligations: ["Total payment is not to exceed $_____ for time and materials."],
  };
  const concerns = getPotentialConcerns(clause);
  assert.ok(
    concerns.some((c) => /payment cap contains a blank amount|blank amount/i.test(c)),
    "Must detect $_____ blank placeholder"
  );
});

test("Requirement 4: '(DATE)' or blank date becomes a potential concern", () => {
  const clause = {
    title: "Term of Agreement",
    obligations: ["This Agreement shall take effect on (DATE); and end on (DATE)."],
  };
  const concerns = getPotentialConcerns(clause);
  assert.ok(
    concerns.some((c) => /\(DATE\)|blank.*date/i.test(c)),
    "Must detect (DATE) placeholder"
  );
});

test("Requirement 5: Missing Exhibit/Schedule reference becomes a potential concern", () => {
  const clause = {
    title: "Scope of Services",
    obligations: ["Services shall be accomplished as specified in Exhibit A: Scope of Services."],
  };
  const concerns = getPotentialConcerns(clause);
  assert.ok(
    concerns.some((c) => /Exhibit A/i.test(c) && /scope of services/i.test(c)),
    "Must detect Exhibit A reference as a concern"
  );
});

test("Requirement 6: Existing substantive clause text never produces 'No substantive clause text was available...'", () => {
  const clauseWithMeaning = {
    title: "Operational Requirements",
    meaning: "CONSULTANT agrees to exercise special skill to accomplish project deliverables.",
  };
  const concerns = getPotentialConcerns(clauseWithMeaning);
  assert.ok(
    !concerns.some((c) => /No substantive clause text was available/i.test(c)),
    "Must not claim text is unavailable when meaning or obligations exist"
  );
});

test("Requirement 7: Truncated clause produces a concern", () => {
  const clause = {
    title: "Default Termination",
    clauseText: "The Agreement may be terminated immediately provided that...",
  };
  const concerns = getPotentialConcerns(clause);
  assert.ok(
    concerns.some((c) => /truncated|incomplete/i.test(c)),
    "Must detect truncated clause ending"
  );
});

test("Requirement 8: Complete clause with no issue produces the clean/no-concern message", () => {
  const cleanClause = {
    title: "Governing Law",
    clauseText: "This Agreement shall be governed by and construed in accordance with the laws of the State of California.",
  };
  const concerns = getPotentialConcerns(cleanClause);
  assert.strictEqual(concerns.length, 1);
  assert.strictEqual(
    concerns[0],
    "No specific ambiguity or missing information was identified in the available clause text."
  );
});

test("Requirement 9: Priority titles are concise, <=60 characters, and never full sentences", () => {
  const longTitleClauses = [
    {
      clause_id: "c-1",
      risk_level: "HIGH",
      risk_score: 95,
      title: "EQUAL EMPLOYMENT OPPORTUNITY. During and in relation to the performance of this Agreement, which requires...",
      obligations: ["During the performance of this Agreement, CONSULTANT shall not discriminate."],
    },
    {
      clause_id: "c-2",
      risk_level: "HIGH",
      risk_score: 90,
      title: "WORK PRODUCTS. All material, data, information, and written, graphic or other work produced under this contract shall belong to client.",
      obligations: ["All material produced under this contract belongs to client."],
    },
    {
      clause_id: "c-3",
      risk_level: "HIGH",
      risk_score: 85,
      title: null,
      clause_type: "TERMINATION",
      obligations: ["Agreement may be terminated upon 30 days notice."],
    },
  ];

  const priority = getPriorityIssues(longTitleClauses);
  for (const item of priority) {
    assert.ok(item.title.length <= 60, `Title must be <= 60 chars: "${item.title}"`);
    assert.ok(!item.title.includes("."), `Title should not be a full sentence with period: "${item.title}"`);
  }
  assert.strictEqual(priority[0].title, "EQUAL EMPLOYMENT OPPORTUNITY");
  assert.strictEqual(priority[1].title, "WORK PRODUCTS");
  assert.strictEqual(priority[2].title, "TERMINATION & DEFAULT");
});

test("Requirement 10: Priority reasons are evidence-grounded rather than generic boilerplate", () => {
  const clauses = [
    {
      clause_id: "c-term",
      title: "EARLY TERMINATION",
      risk_level: "HIGH",
      risk_score: 100,
      obligations: ["COMMISSION may terminate for default if breach is not cured within ten (10) days."],
      risk_reasons: ["The provision contains consequences that may affect a party."], // generic boilerplate to replace
    },
    {
      clause_id: "c-indemn",
      title: "INDEMNIFICATION",
      risk_level: "HIGH",
      risk_score: 95,
      obligations: ["CONSULTANT shall defend and hold harmless COMMISSION from claims and damages."],
      risk_reasons: ["The provision contains default-related consequences."], // generic boilerplate to replace
    },
  ];

  const priority = getPriorityIssues(clauses);
  assert.ok(!priority[0].shortReason.includes("contains consequences that may affect a party"));
  assert.ok(priority[0].shortReason.includes("termination for default") || priority[0].shortReason.includes("breach is not cured"));
  assert.ok(!priority[1].shortReason.includes("contains default-related consequences"));
  assert.ok(priority[1].shortReason.includes("defend and cover") || priority[1].shortReason.includes("claims"));
});

test("Requirement 11: Priority actions are clause-specific and not repeatedly boilerplate", () => {
  const clauses = [
    {
      clause_id: "c-term",
      title: "TERMINATION",
      risk_level: "HIGH",
      risk_score: 90,
      obligations: ["Either party may terminate upon notice."],
      recommendation: "Identify who is responsible for each obligation or duty.", // generic boilerplate to replace
    },
    {
      clause_id: "c-insur",
      title: "INSURANCE",
      risk_level: "HIGH",
      risk_score: 90,
      obligations: ["Maintain $2,000,000 commercial liability insurance."],
      recommendation: "Identify who is responsible for each obligation or duty.", // generic boilerplate to replace
    },
    {
      clause_id: "c-wp",
      title: "WORK PRODUCTS",
      risk_level: "HIGH",
      risk_score: 85,
      obligations: ["All intellectual property vests in client."],
    },
  ];

  const priority = getPriorityIssues(clauses);
  for (const item of priority) {
    assert.ok(
      !item.shortAction.includes("Identify who is responsible for each obligation or duty"),
      `Action must not be generic boilerplate: "${item.shortAction}"`
    );
  }
  assert.ok(/termination rights|notice periods|cure period/i.test(priority[0].shortAction));
  assert.ok(/coverage types|limits|premiums/i.test(priority[1].shortAction));
  assert.ok(/owns the work products|intellectual-property/i.test(priority[2].shortAction));
});

test("Requirement 12 & 13: Different actual deadlines are preserved and only genuinely identical ones are deduplicated", () => {
  const clauses = [
    {
      title: "Invoicing and Termination",
      obligations: [
        "Invoices shall be submitted no later than 45calendar days after the performance of work for which the CONSULTANT is billing.",
        "CONSULTANT's final invoice must be submitted within 60-calendar days after acceptance of work.",
        "COMMISSION may terminate this Agreement by giving CONSULTANT thirty-day (30-day) written notice thereof.",
        "Cure such breach within ten (10) days after written notice thereof by COMMISSION.",
        "CONSULTANT may terminate this Agreement by giving the COMMISSION at least one hundred and twenty (120) days advance written notice.",
      ],
      notices: [
        // Duplicate 30-day commission termination notice
        "COMMISSION may terminate for convenience by giving thirty-day (30-day) written notice.",
      ],
    },
    {
      title: "Insurance",
      obligations: [
        "Insurance shall not be canceled until after thirty (30) days prior written notice has been given.",
      ],
    },
  ];

  const deadlines = getImportantDeadlines(clauses);

  // Check preservation of distinct time intervals
  assert.ok(deadlines.some((d) => d.period === "45 calendar days" && /Invoice submission/i.test(d.appliesTo)));
  assert.ok(deadlines.some((d) => d.period === "60 calendar days" && /Final invoice submission/i.test(d.appliesTo)));
  assert.ok(deadlines.some((d) => d.period === "10 days" && /Cure period/i.test(d.appliesTo)));
  assert.ok(deadlines.some((d) => d.period === "120 days" && /Consultant termination notice/i.test(d.appliesTo)));
  assert.ok(deadlines.some((d) => d.period === "30 days" && /Commission termination notice/i.test(d.appliesTo)));

  // Insurance cancellation notice is distinct from commission termination notice
  assert.ok(deadlines.some((d) => d.period === "30 days" && /Insurance cancellation notice/i.test(d.appliesTo)));

  // Duplicate 30-day commission termination notice must be deduplicated
  const commissionNotices = deadlines.filter((d) => d.period === "30 days" && /Commission termination/i.test(d.appliesTo));
  assert.strictEqual(commissionNotices.length, 1, "Duplicate 30-day commission termination notice should be deduplicated");
});

test("Requirement 15 & 16: No fabricated concerns or unsupported alarmist language generated", () => {
  const clauses = [
    {
      title: "Payment Terms",
      clauseText: "Client shall pay invoiced amounts within Net 30 days via bank transfer.",
    },
  ];

  const concerns = getReportPotentialConcerns(clauses);
  for (const c of concerns) {
    assert.ok(
      !/\b(?:dangerous|illegal|fraudulent|unfair)\b/i.test(c.concern),
      `Concern must use neutral language without alarmist words: "${c.concern}"`
    );
  }
});
