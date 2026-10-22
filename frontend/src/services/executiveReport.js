/**
 * Executive Report Synthesis Service
 *
 * Distills extensive contract analysis into an executive-level summary:
 * 1. Executive Summary (Overall Risk, Score, Counts)
 * 2. Priority Issues (Top 3-5 high-risk clauses with short reason & action)
 * 3. Key Financial Terms (Amounts, fees, payment conditions, limits without text dumps)
 * 4. Key Obligations (Top 5-8 user obligations in concise bullets)
 * 5. Important Deadlines (Notice periods, payment deadlines, cure periods, deduplicated)
 * 6. Potential Concerns (Top 3-5 critical ambiguities, blanks, missing exhibits)
 * 7. Important Clause Relationships (Top 5-8 meaningful dependencies)
 * 8. All Detected Clauses (Collapsible section with Clause Intelligence details)
 */

import {
  getWhatItSays,
  getWhyThisIsImportant,
  getPotentialConcerns,
  getWhatShouldYouDo,
  getClauseSourceText,
  detectClauseCategory,
} from "./clauseIntelligence.js";

/**
 * Clean and shorten priority titles to max 60 chars, never full sentences
 */
export function cleanPriorityTitle(title, clause = null, index = 0) {
  let raw = String(title || "").trim();

  // Strip leading uppercase headings before period, colon, or dashes:
  // e.g. "EQUAL EMPLOYMENT OPPORTUNITY. During and in relation to the performance of this Agreement," -> "EQUAL EMPLOYMENT OPPORTUNITY"
  // e.g. "WORK PRODUCTS. All material, data, information..." -> "WORK PRODUCTS"
  // e.g. "REBATES, KICKBACKS OR OTHER UNLAWFUL CONSIDERATION. The CONSULTANT" -> "REBATES, KICKBACKS OR OTHER UNLAWFUL CONSIDERATION"
  const headingMatch = raw.match(/^([A-Z0-9\s,&/'-]{3,60}?)(?:[.:–—\n]|\s+-\s+)/);
  if (headingMatch && headingMatch[1].trim().length >= 3) {
    raw = headingMatch[1].trim();
  }

  // If raw contains punctuation or sentence starters
  if (raw.length > 60 || raw.includes(".") || /^(?:During|All|In|The|This|Whereas|No person|If)\b/i.test(raw)) {
    const firstPunct = raw.search(/[.:;–—]/);
    if (firstPunct > 3 && firstPunct <= 60) {
      raw = raw.slice(0, firstPunct).trim();
    }
  }

  const sourceText = getClauseSourceText(clause);
  const combined = `${raw} ${clause?.clause_type || ""} ${clause?.category || ""} ${sourceText.slice(0, 300)}`.toLowerCase();

  const isGeneric = !raw || /^clause\s*\d*$/i.test(raw) || raw.length > 60 || /^(?:during|all|in|the|this|whereas|no person|if)\b/i.test(raw);

  if (isGeneric) {
    if (combined.includes("terminat") || combined.includes("cancell") || combined.includes("default")) {
      raw = "TERMINATION & DEFAULT";
    } else if (combined.includes("indemn") || combined.includes("hold harmless") || combined.includes("liabilit")) {
      raw = "INDEMNIFICATION & LIABILITY";
    } else if (combined.includes("work product") || combined.includes("intellectual property") || combined.includes("patent") || combined.includes("copyright")) {
      raw = "WORK PRODUCTS / INTELLECTUAL PROPERTY";
    } else if (combined.includes("insuran")) {
      raw = "INSURANCE";
    } else if (combined.includes("payment") || combined.includes("compensation") || combined.includes("fee") || combined.includes("invoic") || combined.includes("billing")) {
      raw = "PAYMENT & COMPENSATION";
    } else if (combined.includes("confident") || combined.includes("non-disclos") || combined.includes("secrecy")) {
      raw = "CONFIDENTIALITY";
    } else if (combined.includes("privac") || combined.includes("data protection") || combined.includes("gdpr")) {
      raw = "DATA PROTECTION";
    } else if (combined.includes("equal employment") || combined.includes("non-discrimination") || combined.includes("opportunity")) {
      raw = "EQUAL EMPLOYMENT OPPORTUNITY";
    } else if (combined.includes("subcontract") || combined.includes("assign")) {
      raw = "SUBCONTRACTING & ASSIGNMENT";
    } else if (combined.includes("rebate") || combined.includes("kickback") || combined.includes("unlawful")) {
      raw = "UNLAWFUL CONSIDERATION & REBATES";
    } else if (combined.includes("audit") || combined.includes("inspect")) {
      raw = "AUDIT REVIEW PROCEDURES";
    } else if (combined.includes("dispute") || combined.includes("governing law") || combined.includes("arbitrat")) {
      raw = "DISPUTE RESOLUTION";
    } else {
      const clauseNum = clause?.clause_number || (clause?.clause_id && String(clause.clause_id).replace(/^clause-/, "")) || (index + 1);
      raw = `CLAUSE ${clauseNum}`;
    }
  }

  // Strict maximum length: 60 characters
  if (raw.length > 60) {
    raw = raw.slice(0, 57).trim() + "...";
  }

  return raw;
}

export function getPriorityReason(clause, title, rawText) {
  const text = (rawText || getClauseSourceText(clause)).toLowerCase();
  const titleLower = String(title || "").toLowerCase();

  // If clause has an evidence-grounded reason that is NOT generic boilerplate:
  const candidate = (
    clause?.why_it_matters ||
    (Array.isArray(clause?.risk_reasons) ? clause.risk_reasons[0] : "") ||
    ""
  ).trim();

  const isGeneric =
    !candidate ||
    candidate.length < 15 ||
    /^The provision contains consequences/i.test(candidate) ||
    /^The provision contains default-related/i.test(candidate) ||
    /^The provision contains a penalty/i.test(candidate) ||
    /^The provision describes an action/i.test(candidate) ||
    /^The provision contains breach-related/i.test(candidate) ||
    /Specific operational impacts cannot be determined/i.test(candidate);

  if (!isGeneric) {
    let clean = candidate.replace(/^[-•*]\s*/, "");
    if (clean.length > 120) clean = clean.slice(0, 117).trim() + "...";
    return clean;
  }

  // Synthesize evidence-grounded reason based on clause content
  if (titleLower.includes("equal employment") || titleLower.includes("non-discrimination") || text.includes("non-discrimination")) {
    return "The clause mandates non-discrimination and compliance with statutory employment and labor regulations.";
  }
  if (titleLower.includes("rebate") || titleLower.includes("kickback") || titleLower.includes("unlawful") || text.includes("rebate") || text.includes("kickback")) {
    return "The clause prohibits rebates, kickbacks, or unlawful financial considerations and triggers breach remedies.";
  }
  if (titleLower.includes("work product") || titleLower.includes("intellectual property") || text.includes("work product") || text.includes("ownership")) {
    return "The clause assigns rights or ownership over work produced under the agreement.";
  }
  if (titleLower.includes("indemn") || titleLower.includes("liabilit") || text.includes("indemn") || text.includes("hold harmless")) {
    return "The clause may require the consultant to defend and cover specified claims, losses, damages or defense costs arising from specified conduct.";
  }
  if (titleLower.includes("insuran") || text.includes("insuran")) {
    return "The clause requires maintaining specific insurance policies, coverage minimums, and cancellation notices at the consultant's expense.";
  }
  if (titleLower.includes("terminat") || titleLower.includes("cancell") || titleLower.includes("default")) {
    if (text.includes("cure") || text.includes("default")) {
      return "The clause allows termination for default after a breach is not cured within the specified notice period.";
    }
    return "The clause permits contract termination and defines advance notice obligations.";
  }
  if (titleLower.includes("payment") || titleLower.includes("compensation") || text.includes("reimburse") || text.includes("billing rate")) {
    return "The clause establishes payment caps, invoicing requirements, and reimbursement conditions.";
  }
  if (text.includes("terminat") || text.includes("cure")) {
    if (text.includes("cure") || text.includes("default")) {
      return "The clause allows termination for default after a breach is not cured within the specified notice period.";
    }
    return "The clause permits contract termination and defines advance notice obligations.";
  }
  if (titleLower.includes("confident") || text.includes("confident")) {
    return "The clause restricts disclosure of proprietary business information and trade secrets surviving termination.";
  }
  if (titleLower.includes("data protection") || titleLower.includes("privac") || text.includes("personal data")) {
    return "The clause governs processing of personal data and security obligations under privacy laws.";
  }

  const cleanTitle = title || "Contract provision";
  return `Defines high-impact operational obligations and liabilities for ${cleanTitle.toLowerCase()}.`;
}

export function getPriorityAction(clause, title, rawText) {
  const text = (rawText || getClauseSourceText(clause)).toLowerCase();
  const titleLower = String(title || "").toLowerCase();

  // If candidate is NOT the generic "Identify who is responsible for each obligation or duty"
  const candidate = (
    clause?.recommendation ||
    (Array.isArray(clause?.recommendations) ? clause.recommendations[0] : "") ||
    ""
  ).trim();

  const isGeneric =
    !candidate ||
    candidate.length < 15 ||
    /Identify who is responsible for each obligation/i.test(candidate) ||
    /Review requirements cannot be determined/i.test(candidate);

  if (!isGeneric) {
    let clean = candidate.replace(/^[-•*]\s*/, "");
    if (clean.length > 120) clean = clean.slice(0, 117).trim() + "...";
    return clean;
  }

  // Evidence-grounded action
  if (titleLower.includes("equal employment") || titleLower.includes("non-discrimination") || text.includes("non-discrimination")) {
    return "Verify employment compliance procedures, recordkeeping duties, and non-discrimination terms.";
  }
  if (titleLower.includes("rebate") || titleLower.includes("kickback") || titleLower.includes("unlawful") || text.includes("rebate") || text.includes("kickback")) {
    return "Verify compliance standards to ensure no improper financial incentives or conflicts of interest exist.";
  }
  if (titleLower.includes("work product") || titleLower.includes("intellectual property") || text.includes("work product") || text.includes("ownership")) {
    return "Verify who owns the work products and related intellectual-property rights.";
  }
  if (titleLower.includes("indemn") || titleLower.includes("liabilit") || text.includes("indemn") || text.includes("hold harmless")) {
    return "Review the scope of indemnity, covered claims and whether any liability limits apply.";
  }
  if (titleLower.includes("insuran") || text.includes("insuran")) {
    return "Check required coverage types, limits, duration and responsibility for premiums.";
  }
  if (titleLower.includes("terminat") || titleLower.includes("cancell") || titleLower.includes("default")) {
    return "Check the termination rights, notice periods, default triggers and cure period.";
  }
  if (titleLower.includes("payment") || titleLower.includes("compensation") || text.includes("reimburse") || text.includes("billing rate")) {
    return "Verify payment amounts, invoicing requirements, reimbursement conditions and deadlines.";
  }
  if (text.includes("terminat") || text.includes("cure")) {
    return "Check the termination rights, notice periods, default triggers and cure period.";
  }
  if (titleLower.includes("confident") || text.includes("confident")) {
    return "Check what information is protected, permitted disclosures and how long the obligation lasts.";
  }
  if (titleLower.includes("data protection") || titleLower.includes("privac") || text.includes("personal data")) {
    return "Check what data is collected, how it is used/shared and retention requirements.";
  }
  if (titleLower.includes("subcontract") || text.includes("subcontract")) {
    return "Verify whether prior written consent is required before engaging or changing subcontractors.";
  }

  return "Review operational terms, notice triggers, and contractual remedies before signing.";
}

/**
 * 1. Executive Summary Metrics
 */
export function getExecutiveSummaryMetrics(clauses = [], currentSummary = null, passedAnalysis = null) {
  const total =
    currentSummary?.total_clauses ||
    currentSummary?.total_clause_count ||
    clauses.length ||
    0;

  const highCount =
    currentSummary?.risk_summary?.high ??
    currentSummary?.high_risk_clause_count ??
    clauses.filter((c) => String(c?.risk_level || c?.risk || "").toUpperCase() === "HIGH").length;

  const medCount =
    currentSummary?.risk_summary?.medium ??
    currentSummary?.medium_risk_clause_count ??
    clauses.filter((c) => String(c?.risk_level || c?.risk || "").toUpperCase() === "MEDIUM").length;

  const lowCount =
    currentSummary?.risk_summary?.low ??
    currentSummary?.low_risk_clause_count ??
    clauses.filter((c) => String(c?.risk_level || c?.risk || "").toUpperCase() === "LOW").length;

  const overallRisk = String(
    currentSummary?.overall_risk ||
    passedAnalysis?.overall_risk ||
    (highCount > 0 ? "HIGH" : medCount > 0 ? "MEDIUM" : "LOW")
  ).toUpperCase();

  const overallRiskScore = Number(
    currentSummary?.overall_risk_score ??
    passedAnalysis?.overall_risk_score ??
    (total > 0 ? Math.min(100, Math.round((highCount * 30 + medCount * 12 + lowCount * 3) / total * 3)) : 0)
  );

  return {
    overallRisk,
    overallRiskScore,
    riskCounts: { high: highCount, medium: medCount, low: lowCount },
    totalClauses: total,
  };
}

/**
 * 2. Priority Issues (Top 3-5 high-risk clauses)
 */
export function getPriorityIssues(clauses = []) {
  if (!Array.isArray(clauses) || clauses.length === 0) return [];

  // Sort: High risk first, then by risk score descending
  const sorted = [...clauses].sort((a, b) => {
    const riskRank = { HIGH: 3, MEDIUM: 2, LOW: 1, UNKNOWN: 0 };
    const aRisk = String(a?.risk_level || a?.risk || "LOW").toUpperCase();
    const bRisk = String(b?.risk_level || b?.risk || "LOW").toUpperCase();
    const rankDiff = (riskRank[bRisk] || 0) - (riskRank[aRisk] || 0);
    if (rankDiff !== 0) return rankDiff;
    const aScore = a?.risk_score ?? a?.score ?? 0;
    const bScore = b?.risk_score ?? b?.score ?? 0;
    return bScore - aScore;
  });

  // Pick top 3 to 5 clauses
  const topClauses = sorted.slice(0, 5);

  return topClauses.map((clause, idx) => {
    const rawText = getClauseSourceText(clause);
    const clauseNum = clause?.clause_number || (clause?.clause_id && String(clause.clause_id).replace(/^clause-/, "")) || null;
    const title = cleanPriorityTitle(clause?.title, clause, idx);
    const riskLevel = String(clause?.risk_level || clause?.risk || "LOW").toUpperCase();
    const riskScore = clause?.risk_score ?? clause?.score ?? (riskLevel === "HIGH" ? 75 : riskLevel === "MEDIUM" ? 45 : 15);

    const shortReason = getPriorityReason(clause, title, rawText);
    const shortAction = getPriorityAction(clause, title, rawText);

    return {
      clauseId: clause?.clause_id || clause?.id || `priority-${idx}`,
      clauseNumber: clauseNum,
      title,
      riskLevel,
      riskScore,
      shortReason,
      shortAction,
      originalClause: clause,
    };
  });
}

/**
 * Strict validator for financial terms
 */
export function isFinancialConcept(str) {
  if (!str || typeof str !== "string") return false;
  const s = str.trim();
  if (s.length < 2) return false;

  // Strict negative rejections: personnel, project manager, meetings, general performance/skill
  if (/\b(?:personnel|key\s+personnel|project\s+manager|principal\s+in\s+charge|function\s+principal|successor|named\s+in\s+paragraph|removed\s+or\s+replaced|function\s+hereunder|resumes?)\b/i.test(s)) {
    return false;
  }
  if (/\b(?:shall\s+meet\s+with|meetings?|attend\s+meetings?)\b/i.test(s) && !/\$|\b\d+[\d,]*\s*(?:dollars|usd)\b/i.test(s)) {
    return false;
  }
  if (/\b(?:exercise\s+special\s+skill|accomplish\s+the\s+following\s+results|manner\s+reasonably\s+satisfactory)\b/i.test(s) && !/\$|\b\d+[\d,]*\s*(?:dollars|usd)\b/i.test(s)) {
    return false;
  }
  if (/^Name Firm Function Principal in Charge/i.test(s)) {
    return false;
  }

  // Must contain monetary, rate, currency, or explicit financial concept
  const hasCurrency = /\$|\b(?:USD|EUR|GBP|INR|dollars?|cents?)\b/i.test(s);
  const hasMoneyAmount = /\$\s*[\d,]+(?:\.\d+)?|\b\d+[\d,]*\s*(?:dollars|usd|eur|gbp)\b/i.test(s);
  const hasBlankMoney = /\$__+|\$\s*\[\s*_+/i.test(s);
  const hasMoneyPercent = /\b\d+(?:\.\d+)?%\s*(?:interest|late\s+fee|per\s+month|per\s+annum|penalty|rate)\b/i.test(s);
  const hasFinancialKeyword = /\b(?:payment|payments|payable|fee|fees|fixed\s+fee|compensation|reimburse(?:ment|able)?|costs?|pricing|rates?|interest|penalt(?:y|ies)|charge|monetary|insurance\s+amount|insurance\s+coverage|liability\s+(?:monetary\s+)?limit|liability\s+cap|budget|financial\s+limit|financial\s+cap|not\s+to\s+exceed|hourly\s+rate|billing\s+rate)\b/i.test(s);

  if (hasBlankMoney || hasMoneyAmount || hasMoneyPercent) return true;
  if (hasCurrency && hasFinancialKeyword) return true;
  if (hasFinancialKeyword) {
    if (/\b(?:pay|payment|reimburse|fee|cost|rates?|budget|cap|price|not\s+to\s+exceed)\b/i.test(s)) {
      return true;
    }
  }

  return false;
}

/**
 * 3. Key Financial Terms (Amounts, fees, payment conditions, limits without text dumps)
 */
export function getKeyFinancialTerms(clauses = [], currentSummary = null) {
  const items = [];
  const seenValues = new Set();

  const addFinancialItem = (label, value, context = "") => {
    if (!value) return;
    const cleanVal = String(value).trim().replace(/^[-•*]\s*/, "");
    if (!cleanVal || cleanVal.length < 2) return;
    if (!isFinancialConcept(cleanVal)) return;

    // Don't accept multi-sentence paragraphs (max 90 chars)
    const condensedVal = cleanVal.length > 90 ? cleanVal.slice(0, 87).trim() + "..." : cleanVal;
    const key = `${label.toLowerCase()}_${condensedVal.toLowerCase()}`;
    if (!seenValues.has(key)) {
      seenValues.add(key);
      items.push({ label, value: condensedVal, context });
    }
  };

  for (const clause of clauses) {
    const rawTitle = clause?.title || "Financial Provision";
    const title = cleanPriorityTitle(rawTitle, clause);
    const text = getClauseSourceText(clause);

    // 1. Monetary terms / currency values
    const moneyTerms = Array.isArray(clause?.monetary_terms) ? clause.monetary_terms : [];
    for (const m of moneyTerms) {
      if (typeof m === "string" && isFinancialConcept(m)) {
        if (/insurance/i.test(title) || /insurance/i.test(text)) {
          addFinancialItem("Insurance Requirement", m, title);
        } else if (/liabilit/i.test(title) || /cap|maximum|limit/i.test(text)) {
          addFinancialItem("Liability Cap", m, title);
        } else if (/penalty|liquidated/i.test(title) || /penalty/i.test(text)) {
          addFinancialItem("Penalty / Charge", m, title);
        } else if (/not\s+to\s+exceed/i.test(m) || /not\s+to\s+exceed/i.test(text)) {
          addFinancialItem("Payment Cap", m, title);
        } else {
          addFinancialItem("Contract Amount", m, title);
        }
      }
    }

    // 2. Fees & Payment Conditions
    const fees = Array.isArray(clause?.fees) ? clause.fees : [];
    for (const f of fees) {
      if (typeof f === "string" && isFinancialConcept(f)) {
        if (/not\s+to\s+exceed/i.test(f)) {
          addFinancialItem("Payment Cap", f, title);
        } else if (/hourly|rate|fixed\s+fee/i.test(f)) {
          addFinancialItem("Fee / Rate", f, title);
        } else {
          addFinancialItem("Fee / Payment Condition", f, title);
        }
      }
    }

    // 3. Late Payment / Interest
    const lateMatch = text.match(/\b(\d+(?:\.\d+)?%\s*(?:per\s+month|per\s+annum|monthly|annually)?\s*(?:interest|late\s+fee)?)\b/i);
    if (lateMatch) {
      addFinancialItem("Late Payment Fee", `Late fee / interest: ${lateMatch[1]}`, title);
    }

    // 4. Payment terms window (e.g. Net 30, within 15 days)
    const netMatch = text.match(/\b(net\s+\d+|within\s+\d+\s*(?:business\s+days?|days?)\s+of\s+invoice)\b/i);
    if (netMatch) {
      addFinancialItem("Payment Due Window", netMatch[1], title);
    }

    if (items.length >= 6) break;
  }

  // Summary fallback if clauses yielded few items
  const summaryFinance = Array.isArray(currentSummary?.monetary_terms)
    ? currentSummary.monetary_terms
    : Array.isArray(currentSummary?.financial_terms)
    ? currentSummary.financial_terms
    : [];

  if (items.length < 3 && summaryFinance.length > 0) {
    for (const m of summaryFinance) {
      if (typeof m === "string" && isFinancialConcept(m)) {
        addFinancialItem("Contract Financial Term", m, "Financial Overview");
        if (items.length >= 6) break;
      }
    }
  }

  return items.slice(0, 6);
}

/**
 * 4. Key Obligations (5–8 most important user obligations)
 */
export function getKeyObligations(clauses = [], currentSummary = null) {
  const obligations = [];
  const seen = new Set();

  const addObligation = (text) => {
    if (!text) return;
    let clean = String(text).trim().replace(/^[-•*]\s*/, "");
    if (!clean || clean.length < 20) return;

    // Filter noise headers
    if (/^Name Firm Function Principal in Charge/i.test(clean)) return;

    // Keep concise (max 140 chars)
    if (clean.length > 140) {
      const sentenceEnd = clean.search(/[.;]/);
      if (sentenceEnd > 30 && sentenceEnd <= 140) {
        clean = clean.slice(0, sentenceEnd).trim();
      } else {
        clean = clean.slice(0, 137).trim() + "...";
      }
    }
    clean = clean.charAt(0).toUpperCase() + clean.slice(1);
    if (!clean.endsWith(".") && !clean.endsWith("...")) clean += ".";

    const key = clean.toLowerCase().replace(/[^a-z0-9]/g, "");
    if (!seen.has(key)) {
      seen.add(key);
      obligations.push(clean);
    }
  };

  // Rank obligations by importance
  const candidateList = [];

  // 1. From summary
  const summaryObs = Array.isArray(currentSummary?.key_obligations)
    ? currentSummary.key_obligations
    : Array.isArray(currentSummary?.obligations)
    ? currentSummary.obligations
    : [];

  summaryObs.forEach((o) => candidateList.push({ text: o, priority: 5 }));

  // 2. From clauses
  for (const clause of clauses) {
    const risk = String(clause?.risk_level || clause?.risk || "LOW").toUpperCase();
    const riskWeight = risk === "HIGH" ? 8 : risk === "MEDIUM" ? 5 : 2;

    const rawObs = [
      ...(Array.isArray(clause?.obligations) ? clause.obligations : []),
      ...(Array.isArray(clause?.duties) ? clause.duties : []),
    ];

    for (const ob of rawObs) {
      if (typeof ob === "string" && ob.trim().length > 20) {
        let weight = riskWeight;
        if (/\b(?:shall|must|required to|agrees to|obligated to)\b/i.test(ob)) weight += 4;
        if (/\b(?:submit|payment|invoices?|maintain insurance|confidential|comply)\b/i.test(ob)) weight += 3;
        candidateList.push({ text: ob, priority: weight });
      }
    }
  }

  // Sort candidate list by priority descending
  candidateList.sort((a, b) => b.priority - a.priority);

  for (const item of candidateList) {
    addObligation(item.text);
    if (obligations.length >= 8) break;
  }

  return obligations.slice(0, 8);
}

/**
 * 5. Important Deadlines (Notice periods, payment deadlines, cure periods, deduplicated)
 */
export function getImportantDeadlines(clauses = [], currentSummary = null) {
  const deadlines = [];
  const seen = new Set();

  function normalizeNumber(word) {
    const w = String(word).toLowerCase().trim().replace(/[-_]/g, " ");
    if (/^\d+$/.test(w)) return w;
    const map = {
      one: "1", two: "2", three: "3", four: "4", five: "5",
      ten: "10", fifteen: "15", twenty: "20", thirty: "30",
      forty: "40", "forty five": "45", "forty-five": "45",
      sixty: "60", ninety: "90", "one hundred and twenty": "120",
      "one hundred twenty": "120",
    };
    return map[w] || w;
  }

  function normalizeUnit(unit) {
    const u = String(unit).toLowerCase().trim();
    if (u.includes("calendar")) return "calendar days";
    if (u.includes("business")) return "business days";
    if (u.includes("day")) return "days";
    if (u.includes("month")) return "months";
    if (u.includes("year")) return "years";
    return u;
  }

  function detectApplication(sentence) {
    const s = sentence.toLowerCase();
    if (/final\s+invoice/i.test(s)) return "Final invoice submission";
    if (/invoice|billing|bill/i.test(s) && /submit/i.test(s)) return "Invoice submission";
    if (/final\s+billing/i.test(s) && /pay/i.test(s)) return "Payment of final billing";
    if (/cure|remedy/i.test(s)) return "Cure period after breach notice";
    if (/consultant\s+may\s+terminate|contractor\s+may\s+terminate|vendor\s+may\s+terminate/i.test(s)) {
      return "Consultant termination notice";
    }
    if (/commission\s+may\s+terminate|county\s+may\s+terminate|client\s+may\s+terminate|for\s+(?:its\s+)?convenience/i.test(s)) {
      return "Commission termination notice";
    }
    if (/insurance.*(?:cancel|expir)/i.test(s)) return "Insurance cancellation notice";
    if (/audit.*review|review.*audit/i.test(s)) return "Audit review request";
    if (/deliverable|deliverables/i.test(s)) return "Deliverables completion review";
    if (/terminate|termination|cancell/i.test(s)) return "Termination notice";
    if (/renew|renewal/i.test(s)) return "Renewal notice";
    if (/pay|payment/i.test(s)) return "Payment deadline";
    if (/retain|retention|records/i.test(s)) return "Record retention period";
    return "Contract deadline";
  }

  function detectBadgeType(appliesTo) {
    if (/submission/i.test(appliesTo)) return "Submission Deadline";
    if (/cure/i.test(appliesTo)) return "Cure Period";
    if (/payment|billing/i.test(appliesTo)) return "Payment Deadline";
    if (/notice|termination/i.test(appliesTo)) return "Notice Period";
    if (/renewal/i.test(appliesTo)) return "Renewal Notice";
    if (/retention/i.test(appliesTo)) return "Record Retention";
    return "Important Timing";
  }

  function cleanNumberWords(text) {
    return text
      .replace(/\b(?:thirty|forty-five|sixty|ten|twenty|ninety|one hundred (?:and )?twenty)[- ]day\s*\(\s*(\d+)[- ]day\s*\)/gi, "$1 days")
      .replace(/\b(?:thirty|forty-five|sixty|ten|twenty|ninety|one hundred (?:and )?twenty)\s*\(\s*(\d+)\s*\)/gi, "$1");
  }

  const deadlineRegex = /(?:within|no\s+later\s+than|not\s+later\s+than|at\s+least|giving|prior\s+to|after|period\s+of)?\s*(\b(?:\d+|one\s+hundred\s+(?:and\s+)?twenty|thirty|forty-five|sixty|ten|fifteen|twenty|ninety)\b|\d+)(?:\s*\(\s*(\d+)\s*\))?[- ]*(calendar\s+days?|business\s+days?|days?|months?|weeks?|years?)\b/gi;

  for (const clause of clauses) {
    const raw = getClauseSourceText(clause);
    const title = cleanPriorityTitle(clause?.title, clause);

    const allSnippets = [];
    if (clause?.clauseText) allSnippets.push(clause.clauseText);
    else if (clause?.text) allSnippets.push(clause.text);
    else if (clause?.content) allSnippets.push(clause.content);

    if (Array.isArray(clause?.notices)) allSnippets.push(...clause.notices);
    if (Array.isArray(clause?.obligations)) allSnippets.push(...clause.obligations);
    if (Array.isArray(clause?.conditions)) allSnippets.push(...clause.conditions);
    if (Array.isArray(clause?.triggers)) allSnippets.push(...clause.triggers);
    if (Array.isArray(clause?.consequences)) allSnippets.push(...clause.consequences);

    if (allSnippets.length === 0 && raw) {
      allSnippets.push(raw);
    }

    const uniqueSnippets = [...new Set(allSnippets.filter((s) => typeof s === "string" && s.trim()))];

    for (const rawSnippet of uniqueSnippets) {
      const s = cleanNumberWords(rawSnippet);
      const regex = new RegExp(deadlineRegex.source, "gi");
      let m;
      while ((m = regex.exec(s)) !== null) {
        const rawNum = m[2] || m[1];
        const num = normalizeNumber(rawNum);
        const unit = normalizeUnit(m[3]);
        const period = `${num} ${unit === "calendar days" && /^\d+$/.test(num) ? "calendar days" : unit}`;

        const snippetWindow = s.slice(Math.max(0, m.index - 160), Math.min(s.length, m.index + 160));
        const appliesTo = detectApplication(snippetWindow);
        const dedupeKey = `${num}_${unit}_${appliesTo}`.toLowerCase();

        if (!seen.has(dedupeKey)) {
          seen.add(dedupeKey);
          const type = detectBadgeType(appliesTo);
          deadlines.push({
            type,
            text: `${period} — ${appliesTo}`,
            period,
            appliesTo,
            clauseTitle: title || "Contract Provision",
          });
          if (deadlines.length >= 8) break;
        }
      }
      if (deadlines.length >= 8) break;
    }
    if (deadlines.length >= 8) break;
  }

  // Fallback to explicit clause.deadlines or durations if sparse
  if (deadlines.length < 3) {
    for (const clause of clauses) {
      const dates = [
        ...(Array.isArray(clause?.deadlines) ? clause.deadlines : []),
        ...(Array.isArray(clause?.durations) ? clause.durations : []),
      ];
      for (const d of dates) {
        if (!d || typeof d !== "string") continue;
        const clean = d.trim();
        const dedupeKey = clean.toLowerCase();
        if (!seen.has(dedupeKey)) {
          seen.add(dedupeKey);
          deadlines.push({
            type: "Critical Timing",
            text: clean,
            period: clean,
            appliesTo: "Contract Timing",
            clauseTitle: cleanPriorityTitle(clause?.title, clause) || "Contract Provision",
          });
          if (deadlines.length >= 8) break;
        }
      }
      if (deadlines.length >= 8) break;
    }
  }

  return deadlines.slice(0, 8);
}

/**
 * 6. Potential Concerns (Top 3-5 critical ambiguities, blanks, missing documents)
 */
export function getReportPotentialConcerns(clauses = []) {
  const concerns = [];
  const seen = new Set();

  for (const clause of clauses) {
    const rawText = getClauseSourceText(clause);
    const clauseConcerns = getPotentialConcerns(clause, rawText);
    const cleanTitle = cleanPriorityTitle(clause?.title, clause);

    for (const c of clauseConcerns) {
      if (!c) continue;
      // Skip the default clean fallback string when aggregating across clauses
      if (/No specific ambiguity or missing information/i.test(c)) continue;
      if (/No substantive clause text was available/i.test(c)) continue;

      const clean = String(c).trim();
      const key = clean.toLowerCase();
      if (!seen.has(key)) {
        seen.add(key);
        concerns.push({
          clauseTitle: cleanTitle || "Contract Clause",
          concern: clean,
        });
        if (concerns.length >= 5) break;
      }
    }
    if (concerns.length >= 5) break;
  }

  if (concerns.length === 0) {
    return [
      {
        clauseTitle: "Contract Document",
        concern: "No specific ambiguity or missing information was identified in the available contract text.",
      },
    ];
  }

  return concerns.slice(0, 5);
}

/**
 * 7. Important Clause Relationships (Top 5-8 meaningful dependencies)
 */
export function getMeaningfulRelationships(relationshipsData = null, clauses = []) {
  const rawRels = Array.isArray(relationshipsData?.relationships)
    ? relationshipsData.relationships
    : Array.isArray(relationshipsData)
    ? relationshipsData
    : [];

  if (rawRels.length === 0) return [];

  // Map clause ID to human title
  const titleMap = new Map();
  for (const c of clauses) {
    const id = c?.clause_id || c?.id;
    if (id) {
      const num = c?.clause_number || id.replace(/^clause-/, "");
      titleMap.set(id, cleanPriorityTitle(c.title, c) || `Clause ${num}`);
    }
  }

  const result = [];
  const seenPairs = new Set();

  for (const rel of rawRels) {
    const srcId = rel?.source_clause_id || "";
    const tgtId = rel?.target_clause_id || "";
    const type = (rel?.relationship_type || "DEPENDS_ON").toUpperCase().replace(/_/g, " ");

    const srcTitle = titleMap.get(srcId) || srcId || "Source Clause";
    const tgtTitle = titleMap.get(tgtId) || tgtId || "Target Clause";

    const pairKey = `${srcTitle}_${tgtTitle}_${type}`.toLowerCase();
    if (!seenPairs.has(pairKey)) {
      seenPairs.add(pairKey);
      result.push({
        sourceTitle: srcTitle,
        targetTitle: tgtTitle,
        relationshipType: type,
        evidence: rel?.evidence ? String(rel.evidence).slice(0, 110) : "",
        confidence: rel?.confidence ?? 1.0,
      });
      if (result.length >= 8) break;
    }
  }

  return result.slice(0, 8);
}
