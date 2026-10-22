import test from "node:test";
import assert from "node:assert";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

import { getContracts } from "./api/contractsApi.js";
import {
  computeDashboardMetrics,
  formatContractDate,
} from "./services/dashboardService.js";

const __dirname = path.dirname(fileURLToPath(import.meta.url));

// Sample test contracts with known dates and scores
const mockContracts = [
  {
    id: "contract-1",
    filename: "Vendor_Agreement_Alpha.pdf",
    file_type: "pdf",
    created_at: "2026-01-10T10:00:00Z",
    status: "analyzed",
    overall_risk: "MEDIUM",
    overall_risk_score: 50,
  },
  {
    id: "contract-2",
    filename: "SaaS_Subscription_Beta.docx",
    file_type: "docx",
    created_at: "2026-02-15T10:00:00Z",
    status: "analyzed",
    overall_risk: "HIGH",
    overall_risk_score: 85,
  },
  {
    id: "contract-3",
    filename: "Privacy_Policy_Gamma.pdf",
    file_type: "pdf",
    created_at: "2026-03-20T10:00:00Z",
    status: "analyzed",
    overall_risk: "LOW",
    overall_risk_score: 25,
  },
];

/* -------------------------------------------------------------
   1. REFRESH API & CACHE-BUSTING VERIFICATION
------------------------------------------------------------- */
test("getContracts API sends Cache-Control and Pragma no-cache headers", () => {
  const contractsApiPath = path.join(__dirname, "api", "contractsApi.js");
  const source = fs.readFileSync(contractsApiPath, "utf-8");

  assert.ok(
    /["']?Cache-Control["']?\s*:\s*["']no-cache["']/i.test(source),
    "contractsApi.js must include Cache-Control no-cache header to prevent stale caches"
  );
  assert.ok(
    /["']?Pragma["']?\s*:\s*["']no-cache["']/i.test(source),
    "contractsApi.js must include Pragma no-cache header"
  );
});

test("App.jsx implements concurrency guard to prevent duplicate refresh requests", () => {
  const appPath = path.join(__dirname, "App.jsx");
  const source = fs.readFileSync(appPath, "utf-8");

  assert.ok(
    source.includes("isRefreshingContractsRef.current"),
    "refreshContracts in App.jsx must guard against concurrent execution using a ref lock"
  );
  assert.ok(
    source.includes("if (isRefreshingContractsRef.current) return;"),
    "refreshContracts must return early if already in flight"
  );
});

/* -------------------------------------------------------------
   2. DASHBOARD REFRESH LOADING & DISABLED STATE
------------------------------------------------------------- */
test("Dashboard button in App.jsx binds handleRefreshClick, disabled state, and 'Refreshing...' feedback", () => {
  const appPath = path.join(__dirname, "App.jsx");
  const source = fs.readFileSync(appPath, "utf-8");

  // Verify handleRefreshClick handles loading and concurrency
  assert.ok(
    source.includes("const isBusy = Boolean(contractsLoading || isRefreshing);"),
    "Dashboard must compute isBusy from contractsLoading and isRefreshing"
  );
  assert.ok(
    source.includes("if (isBusy) return;"),
    "handleRefreshClick must return early if isBusy"
  );
  assert.ok(
    source.includes("disabled={isBusy}"),
    "Refresh button must be disabled when busy"
  );
  assert.ok(
    source.includes('{isBusy ? "Refreshing..." : "Refresh"}'),
    "Refresh button text must toggle to 'Refreshing...' when busy"
  );
  assert.ok(
    source.includes("Refreshing workspace contracts..."),
    "Header workspace status must indicate refreshing state to the user"
  );
});

/* -------------------------------------------------------------
   3. API FAILURE HANDLING WITH ERROR MESSAGE & RETRY OPTION
------------------------------------------------------------- */
test("Dashboard in App.jsx renders error alert banner with retry button on API failure with existing contracts", () => {
  const appPath = path.join(__dirname, "App.jsx");
  const source = fs.readFileSync(appPath, "utf-8");

  // Verify dashboard-alert-banner is rendered when contractsError is present and contracts exist
  assert.ok(
    source.includes("contractsError && totalContracts > 0"),
    "App.jsx must check contractsError and totalContracts > 0 for banner"
  );
  assert.ok(
    source.includes('className="dashboard-alert-banner error"'),
    "Must render dashboard-alert-banner error"
  );
  assert.ok(
    source.includes('className="secondary-button dashboard-retry-btn"'),
    "Must render dashboard-retry-btn"
  );
  assert.ok(
    source.includes('{isBusy ? "Retrying..." : "Retry"}'),
    "Retry button must toggle state while retrying"
  );
});

test("Dashboard in App.jsx renders full-page error state with retry when library is empty", () => {
  const appPath = path.join(__dirname, "App.jsx");
  const source = fs.readFileSync(appPath, "utf-8");

  assert.ok(
    source.includes("contractsError && totalContracts === 0"),
    "Empty library error condition must be handled"
  );
  assert.ok(
    source.includes("Retry Connection"),
    "Empty library error state must provide a Retry Connection button"
  );
});

/* -------------------------------------------------------------
   4. DYNAMIC DATA UPDATES WITHOUT RELOAD
------------------------------------------------------------- */
test("computeDashboardMetrics updates statistics dynamically when contract data changes", () => {
  // Initial state with 1 contract
  const initial = computeDashboardMetrics([mockContracts[0]]);
  assert.strictEqual(initial.totalContracts, 1);
  assert.strictEqual(initial.avgRiskScore, 50);
  assert.strictEqual(initial.highRiskContracts.length, 0);
  assert.strictEqual(initial.medRiskContracts.length, 1);
  assert.strictEqual(initial.lowRiskContracts.length, 0);

  // Updated state with 3 contracts (simulating successful refresh)
  const updated = computeDashboardMetrics(mockContracts);
  assert.strictEqual(updated.totalContracts, 3);
  // (50 + 85 + 25) / 3 = 53.33 -> 53
  assert.strictEqual(updated.avgRiskScore, 53);
  assert.strictEqual(updated.highRiskContracts.length, 1);
  assert.strictEqual(updated.medRiskContracts.length, 1);
  assert.strictEqual(updated.lowRiskContracts.length, 1);
  assert.strictEqual(updated.highPct, 33);
  assert.strictEqual(updated.medPct, 33);
  assert.strictEqual(updated.lowPct, 34);
});

/* -------------------------------------------------------------
   5. RISK TREND VS RECENT CONTRACTS SORT ORDER & PURPOSE
------------------------------------------------------------- */
test("Recent Contracts orders items strictly by newest date first (descending)", () => {
  // Scrambled order input
  const scrambled = [mockContracts[0], mockContracts[2], mockContracts[1]];
  const metrics = computeDashboardMetrics(scrambled);

  // Recent Contracts must be Gamma (2026-03-20) -> Beta (2026-02-15) -> Alpha (2026-01-10)
  assert.strictEqual(metrics.recentContracts.length, 3);
  assert.strictEqual(metrics.recentContracts[0].id, "contract-3"); // Gamma
  assert.strictEqual(metrics.recentContracts[1].id, "contract-2"); // Beta
  assert.strictEqual(metrics.recentContracts[2].id, "contract-1"); // Alpha
});

test("Recent Contracts caps results to top 5 most recent", () => {
  const sixContracts = [
    ...mockContracts,
    { id: "c4", filename: "c4.pdf", created_at: "2026-04-01T00:00:00Z", overall_risk_score: 40 },
    { id: "c5", filename: "c5.pdf", created_at: "2026-05-01T00:00:00Z", overall_risk_score: 30 },
    { id: "c6", filename: "c6.pdf", created_at: "2026-06-01T00:00:00Z", overall_risk_score: 20 },
  ];
  const metrics = computeDashboardMetrics(sixContracts);

  assert.strictEqual(metrics.recentContracts.length, 5);
  // Most recent should be c6 (June)
  assert.strictEqual(metrics.recentContracts[0].id, "c6");
  assert.strictEqual(metrics.recentContracts[1].id, "c5");
});

test("Risk Trend Across Additions orders items strictly chronological (oldest to newest)", () => {
  // Scrambled order input
  const scrambled = [mockContracts[2], mockContracts[0], mockContracts[1]];
  const metrics = computeDashboardMetrics(scrambled);

  assert.strictEqual(metrics.hasTrend, true);
  assert.strictEqual(metrics.chronologicalContracts.length, 3);
  // Chronological: Alpha (Jan, #1) -> Beta (Feb, #2) -> Gamma (Mar, #3)
  assert.strictEqual(metrics.chronologicalContracts[0].id, "contract-1");
  assert.strictEqual(metrics.chronologicalContracts[1].id, "contract-2");
  assert.strictEqual(metrics.chronologicalContracts[2].id, "contract-3");
});

test("Risk Trend accurately calculates mathematical comparison without fabricating trends", () => {
  // Alpha (50), Beta (85). Prior baseline avg was (50 + 85) / 2 = 68.
  // Gamma (25) < 68 -> strictly lowered portfolio risk
  const metrics = computeDashboardMetrics(mockContracts);

  assert.strictEqual(metrics.latestScored.id, "contract-3");
  assert.strictEqual(metrics.previousAvgScore, 68);
  assert.strictEqual(
    metrics.trendSummaryText,
    "Recent addition (Privacy_Policy_Gamma.pdf) lowered portfolio risk: scored 25/100 vs previous average of 68/100."
  );
});

test("Risk Trend accurately notes higher risk when latest contract scores above previous baseline", () => {
  // Alpha (50, Jan), Delta (90, Feb).
  // 90 > 50 -> introduced higher risk
  const higherRiskSet = [
    mockContracts[0],
    {
      id: "contract-delta",
      filename: "Risky_Licensing_Delta.pdf",
      file_type: "pdf",
      created_at: "2026-04-01T10:00:00Z",
      status: "analyzed",
      overall_risk: "HIGH",
      overall_risk_score: 90,
    },
  ];

  const metrics = computeDashboardMetrics(higherRiskSet);
  assert.strictEqual(
    metrics.trendSummaryText,
    "Recent addition (Risky_Licensing_Delta.pdf) introduced higher risk: scored 90/100 vs previous average of 50/100."
  );
});

test("Risk Trend accurately notes matched baseline when latest contract matches previous average", () => {
  const matchedSet = [
    mockContracts[0], // 50
    {
      id: "contract-matched",
      filename: "Standard_NDA.pdf",
      file_type: "pdf",
      created_at: "2026-05-01T10:00:00Z",
      status: "analyzed",
      overall_risk: "MEDIUM",
      overall_risk_score: 50,
    },
  ];

  const metrics = computeDashboardMetrics(matchedSet);
  assert.strictEqual(
    metrics.trendSummaryText,
    "Recent addition (Standard_NDA.pdf) matched baseline risk at 50/100."
  );
});

test("Risk Trend is not active when fewer than 2 scored contracts exist", () => {
  const single = computeDashboardMetrics([mockContracts[0]]);
  assert.strictEqual(single.hasTrend, false);
  assert.strictEqual(single.chronologicalContracts.length, 1);
  assert.strictEqual(single.latestScored, null);

  const empty = computeDashboardMetrics([]);
  assert.strictEqual(empty.hasTrend, false);
  assert.strictEqual(empty.chronologicalContracts.length, 0);
});

/* -------------------------------------------------------------
   6. DATE FORMATTING UTILITY
------------------------------------------------------------- */
test("formatContractDate formats dates reliably and handles invalid/missing values", () => {
  assert.strictEqual(formatContractDate(null), "Unknown date");
  assert.strictEqual(formatContractDate(""), "Unknown date");
  assert.strictEqual(formatContractDate("invalid-date-string"), "Unknown date");

  const formatted = formatContractDate("2026-01-10T10:00:00Z");
  assert.ok(formatted.includes("2026") && formatted.includes("Jan"));
});
