/**
 * Dashboard Service
 *
 * Provides pure business logic and deterministic calculations for:
 * - Portfolio statistics and risk distribution
 * - Chronological Risk Trend across contract additions
 * - Recent Contracts tracking
 * - Date formatting
 */

export function formatContractDate(dateStr) {
  if (!dateStr) return "Unknown date";
  try {
    const d = new Date(dateStr);
    if (isNaN(d.getTime())) return "Unknown date";
    return d.toLocaleDateString(undefined, {
      month: "short",
      day: "numeric",
      year: "numeric",
    });
  } catch {
    return "Unknown date";
  }
}

export function computeDashboardMetrics(contracts = []) {
  const safeList = Array.isArray(contracts) ? contracts : [];
  const totalContracts = safeList.length;

  const highRiskContracts = safeList.filter((c) => {
    const r = String(c?.overall_risk || "").toLowerCase();
    return r === "high";
  });

  const medRiskContracts = safeList.filter((c) => {
    const r = String(c?.overall_risk || "").toLowerCase();
    return r === "medium" || r === "med";
  });

  const lowRiskContracts = safeList.filter((c) => {
    const r = String(c?.overall_risk || "").toLowerCase();
    return r === "low";
  });

  const scoredContracts = safeList.filter(
    (c) => typeof c?.overall_risk_score === "number" && c.overall_risk_score >= 0
  );

  const avgRiskScore =
    scoredContracts.length > 0
      ? Math.round(
          scoredContracts.reduce((acc, c) => acc + c.overall_risk_score, 0) /
            scoredContracts.length
        )
      : null;

  const analyzedContracts = safeList.filter((c) => {
    const status = String(c?.status || "").toLowerCase();
    return (
      status === "analyzed" ||
      status === "ready" ||
      Boolean(c?.overall_risk) ||
      (typeof c?.overall_risk_score === "number" && c.overall_risk_score > 0)
    );
  }).length;

  const ratedCount =
    highRiskContracts.length + medRiskContracts.length + lowRiskContracts.length;
  const riskBase = ratedCount > 0 ? ratedCount : 1;
  const highPct =
    ratedCount > 0 ? Math.round((highRiskContracts.length / riskBase) * 100) : 0;
  const medPct =
    ratedCount > 0 ? Math.round((medRiskContracts.length / riskBase) * 100) : 0;
  const lowPct = ratedCount > 0 ? Math.max(0, 100 - highPct - medPct) : 0;

  // Recent Contracts: Strictly newest additions first (descending by created_at)
  const recentContracts = [...safeList]
    .sort((a, b) => {
      const timeA = a.created_at ? new Date(a.created_at).getTime() : 0;
      const timeB = b.created_at ? new Date(b.created_at).getTime() : 0;
      if (timeB !== timeA) return timeB - timeA;
      return String(b.id || "").localeCompare(String(a.id || ""));
    })
    .slice(0, 5);

  // Attention Contracts: High risk contracts sorted by highest risk score descending
  const attentionContracts = [...highRiskContracts].sort(
    (a, b) => (b.overall_risk_score || 0) - (a.overall_risk_score || 0)
  );

  // Chronological Contracts: Scored contracts strictly chronological (oldest to newest)
  const chronologicalContracts = [...scoredContracts].sort((a, b) => {
    const timeA = a.created_at ? new Date(a.created_at).getTime() : 0;
    const timeB = b.created_at ? new Date(b.created_at).getTime() : 0;
    if (timeA !== timeB) return timeA - timeB;
    return String(a.id || "").localeCompare(String(b.id || ""));
  });

  const hasTrend = chronologicalContracts.length >= 2;
  const latestScored = hasTrend
    ? chronologicalContracts[chronologicalContracts.length - 1]
    : null;
  const previousScored = hasTrend
    ? chronologicalContracts.slice(0, chronologicalContracts.length - 1)
    : [];
  const previousAvgScore =
    previousScored.length > 0
      ? Math.round(
          previousScored.reduce((acc, c) => acc + (c.overall_risk_score || 0), 0) /
            previousScored.length
        )
      : null;

  let trendSummaryText = "Tracking chronological contract evaluations.";
  if (latestScored && previousAvgScore !== null) {
    if (latestScored.overall_risk_score < previousAvgScore) {
      trendSummaryText = `Recent addition (${latestScored.filename}) lowered portfolio risk: scored ${latestScored.overall_risk_score}/100 vs previous average of ${previousAvgScore}/100.`;
    } else if (latestScored.overall_risk_score > previousAvgScore) {
      trendSummaryText = `Recent addition (${latestScored.filename}) introduced higher risk: scored ${latestScored.overall_risk_score}/100 vs previous average of ${previousAvgScore}/100.`;
    } else {
      trendSummaryText = `Recent addition (${latestScored.filename}) matched baseline risk at ${latestScored.overall_risk_score}/100.`;
    }
  }

  return {
    totalContracts,
    highRiskContracts,
    medRiskContracts,
    lowRiskContracts,
    scoredContracts,
    avgRiskScore,
    analyzedContracts,
    ratedCount,
    highPct,
    medPct,
    lowPct,
    recentContracts,
    attentionContracts,
    chronologicalContracts,
    hasTrend,
    latestScored,
    previousScored,
    previousAvgScore,
    trendSummaryText,
  };
}
