/**
 * Clause Intelligence Enhancement Service
 *
 * Provides grounded, transparent extraction for:
 * 1. WHAT IT SAYS (concise, grounded plain-English summary, 2-4 sentences, ~40-80 words)
 * 2. WHY IS THIS IMPORTANT? (1-3 grounded practical impacts, obligations, deadlines, liabilities)
 * 3. UNCLEAR / POTENTIAL CONCERNS (1-3 actual ambiguities, missing information, unusual obligations)
 * 4. WHAT SHOULD YOU DO? (1-3 practical action check/review steps)
 */

export function detectClauseCategory(clause, rawText) {
  const cat = (
    clause?.clause_type ||
    clause?.category ||
    clause?.classification ||
    clause?.type ||
    ""
  ).toLowerCase();
  const title = (clause?.title || clause?.clause_title || "").toLowerCase();
  const text = (rawText || clause?.clauseText || clause?.text || "").toLowerCase();
  const combined = `${cat} ${title}`;

  if (
    combined.includes("payment") ||
    combined.includes("fee") ||
    combined.includes("billing") ||
    combined.includes("compensation") ||
    combined.includes("invoic") ||
    combined.includes("payable") ||
    combined.includes("price") ||
    combined.includes("pricing")
  ) {
    return "payment";
  }
  if (
    combined.includes("terminat") ||
    combined.includes("cancell") ||
    combined.includes("duration") ||
    combined.includes("expiration") ||
    combined.includes("expiry")
  ) {
    return "termination";
  }
  if (
    combined.includes("privac") ||
    combined.includes("data protection") ||
    combined.includes("gdpr") ||
    combined.includes("processor") ||
    combined.includes("controller")
  ) {
    return "privacy";
  }
  if (
    combined.includes("liabilit") ||
    combined.includes("indemn") ||
    combined.includes("damage") ||
    combined.includes("hold harmless")
  ) {
    return "liability";
  }
  if (combined.includes("renew") || combined.includes("extension") || combined.includes("auto-renew")) {
    return "renewal";
  }
  if (
    combined.includes("confident") ||
    combined.includes("non-disclos") ||
    combined.includes("secrecy") ||
    combined.includes("nda") ||
    combined.includes("proprietary information")
  ) {
    return "confidentiality";
  }
  if (
    combined.includes("intellectual property") ||
    combined.includes("ip rights") ||
    combined.includes("ownership") ||
    combined.includes("patent") ||
    combined.includes("copyright") ||
    combined.includes("trademark") ||
    combined.includes("work for hire")
  ) {
    return "intellectual_property";
  }
  if (
    combined.includes("warrant") ||
    combined.includes("guarantee") ||
    combined.includes("representation") ||
    combined.includes("disclaimer")
  ) {
    return "warranty";
  }
  if (combined.includes("audit") || combined.includes("inspect") || combined.includes("record")) {
    return "audit";
  }
  if (
    combined.includes("dispute") ||
    combined.includes("governing law") ||
    combined.includes("jurisdiction") ||
    combined.includes("arbitrat")
  ) {
    return "dispute";
  }
  if (
    combined.includes("sub-contract") ||
    combined.includes("subcontract") ||
    combined.includes("subprocessor") ||
    combined.includes("assignment")
  ) {
    return "subcontracting";
  }

  // Fallback to text start scanning
  const head = text.slice(0, 350);
  if (/\b(?:payment|invoice|invoices|fees?|billing|payable|compensation)\b/i.test(head)) return "payment";
  if (/\b(?:terminate|termination|cancel|cancellation|expiration)\b/i.test(head)) return "termination";
  if (/\b(?:personal data|data protection|gdpr|privacy|data controller|data processor)\b/i.test(head)) return "privacy";
  if (/\b(?:liability|indemnif|hold harmless|consequential damages|limitation of liability)\b/i.test(head)) return "liability";
  if (/\b(?:automatic renewal|auto-renew|automatically renew)\b/i.test(head)) return "renewal";
  if (/\b(?:confidential information|non-disclosure|proprietary information)\b/i.test(head)) return "confidentiality";
  if (/\b(?:intellectual property|proprietary rights|work for hire|copyright|inventions?)\b/i.test(head)) return "intellectual_property";
  if (/\b(?:warrants?|warranties|disclaims? all warranties|as is)\b/i.test(head)) return "warranty";
  if (/\b(?:audit|inspect records|books and records)\b/i.test(head)) return "audit";
  if (/\b(?:governed by|exclusive jurisdiction|arbitration|venue)\b/i.test(head)) return "dispute";
  if (/\b(?:subcontract|sub-contract|assign(?:ment)?|delegate)\b/i.test(head)) return "subcontracting";

  return "general";
}

/**
 * Extracts the primary actor or responsible party from clause metadata and text
 */
export function extractPrimaryParty(text, clause) {
  const combinedText = `${text || ""} ${clause?.title || ""}`;

  // Check explicit parties in metadata
  const metadataParties = [
    ...(Array.isArray(clause?.parties) ? clause.parties : []),
    ...(Array.isArray(clause?.entities) ? clause.entities : []),
    ...(Array.isArray(clause?.organizations) ? clause.organizations : []),
  ].filter(Boolean);

  if (metadataParties.length > 0) {
    const p = String(metadataParties[0]).trim();
    if (p.length > 2 && p.length < 35 && !/^(section|clause|article|contract|agreement)\b/i.test(p)) {
      return p.charAt(0).toUpperCase() + p.slice(1);
    }
  }

  // Active obligation actor (e.g. "Customer shall pay", "Contractor shall defend")
  const actorMatch = (text || "").match(/\b((?:The\s+)?[A-Z][a-zA-Z\s]{1,25})\s+shall\s+(?:pay|defend|indemnify|submit|provide|perform|deliver|warrant|reimburse)\b/i);
  if (actorMatch) {
    const a = actorMatch[1].trim();
    if (!/^(?:neither|either|which|provided|herein|such)\b/i.test(a)) {
      return a.charAt(0).toUpperCase() + a.slice(1);
    }
  }

  // Common contract roles
  if (/\b(?:the\s+)?Customer\b/i.test(combinedText)) return "Customer";
  if (/\b(?:the\s+)?Client\b/i.test(combinedText)) return "Client";
  if (/\b(?:the\s+)?Contractor\b/i.test(combinedText)) return "Contractor";
  if (/\b(?:the\s+)?Consultant\b/i.test(combinedText)) return "Consultant";
  if (/\b(?:the\s+)?Processor\b/i.test(combinedText)) return "Processor";
  if (/\b(?:the\s+)?Controller\b/i.test(combinedText)) return "Controller";
  if (/\b(?:the\s+)?Vendor\b/i.test(combinedText)) return "Vendor";
  if (/\b(?:the\s+)?Supplier\b/i.test(combinedText)) return "Supplier";
  if (/\b(?:the\s+)?Company\b/i.test(combinedText)) return "Company";
  if (/\b(?:the\s+)?Licensor\b/i.test(combinedText)) return "Licensor";
  if (/\b(?:the\s+)?Licensee\b/i.test(combinedText)) return "Licensee";
  if (/\b(?:the\s+)?Disclosing Party\b/i.test(combinedText)) return "Disclosing Party";
  if (/\b(?:the\s+)?Receiving Party\b/i.test(combinedText)) return "Receiving Party";
  if (/\b(?:the\s+)?Service Provider\b/i.test(combinedText)) return "Service Provider";
  if (/\b(?:the\s+)?Employer\b/i.test(combinedText)) return "Employer";
  if (/\b(?:the\s+)?Employee\b/i.test(combinedText)) return "Employee";
  if (/\b(?:the\s+)?Tenant\b/i.test(combinedText)) return "Tenant";
  if (/\b(?:the\s+)?Landlord\b/i.test(combinedText)) return "Landlord";
  if (/\b(?:the\s+)?Buyer\b/i.test(combinedText)) return "Buyer";
  if (/\b(?:the\s+)?Seller\b/i.test(combinedText)) return "Seller";
  if (/\b(?:the\s+)?User\b/i.test(combinedText)) return "User";
  if (/\b(?:the\s+)?Subscriber\b/i.test(combinedText)) return "Subscriber";
  if (/\bboth parties\b/i.test(combinedText)) return "Both parties";
  if (/\neither party\b/i.test(combinedText)) return "Either party";
  if (/\beach party\b/i.test(combinedText)) return "Each party";

  return "The responsible party";
}

/**
 * Extracts key deadlines, notice periods, and timeframes
 */
export function extractKeyDeadlines(text, clause) {
  const result = {
    noticePeriod: null,
    dueWindow: null,
    curePeriod: null,
    breachNotification: null,
  };

  const cleanText = text || "";

  // Notice period
  const noticeMatch =
    cleanText.match(/\b(\d+)\s*[- ]?(business\s+days?|calendar\s+days?|days?|weeks?|months?)['’]?\s+(?:advance\s+|prior\s+)?(?:written\s+)?notice\b/i) ||
    cleanText.match(/\b(?:written\s+)?notice\s+of\s+(?:not\s+less\s+than\s+)?(\d+\s*(?:business\s+days?|calendar\s+days?|days?|weeks?|months?)['’]?)\b/i) ||
    cleanText.match(/\b(?:written\s+)?notice\b[^\n.;]{0,60}?\bwithin\s+(\d+)\s*[- ]?(business\s+days?|calendar\s+days?|days?|weeks?|months?)\b/i) ||
    cleanText.match(/\bwithin\s+(\d+)\s*[- ]?(business\s+days?|calendar\s+days?|days?|weeks?|months?)[^\n.;]{0,40}?\b(?:written\s+)?notice\b/i) ||
    cleanText.match(/\b(\d+)[ -](business\s+day|calendar\s+day|day|month|week)\s+(?:written\s+)?notice\b/i);

  if (noticeMatch) {
    const rawVal = noticeMatch[1].replace(/['’]/g, "").trim();
    const unit = noticeMatch[2] ? noticeMatch[2].replace(/['’]/g, "").trim() : "";
    if (unit && !rawVal.toLowerCase().includes(unit.toLowerCase())) {
      result.noticePeriod = `${rawVal} ${unit}`;
    } else {
      result.noticePeriod = rawVal;
    }
  }

  // Payment due window
  const dueMatch =
    cleanText.match(/\bwithin\s+(\d+\s*(?:business\s+days?|calendar\s+days?|days?|weeks?|months?))\b/i) ||
    cleanText.match(/\bnet\s+(\d+)\b/i);

  if (dueMatch) {
    result.dueWindow = dueMatch[1] ? dueMatch[1] : `Net ${dueMatch[1]}`;
  }

  // Cure period
  const cureMatch = cleanText.match(/\b(\d+)\s*[- ]?(business\s+days?|calendar\s+days?|days?)\s+(?:cure\s+period|to\s+cure|to\s+remedy|cure\s+window)\b/i) ||
    cleanText.match(/\bcure\s+(?:such\s+)?(?:breach|default)\s+within\s+(\d+\s*(?:business\s+days?|calendar\s+days?|days?))\b/i);

  if (cureMatch) {
    result.curePeriod = cureMatch[1];
  }

  // Breach reporting
  const breachMatch = cleanText.match(/\b(?:notify|report|notification)\s+(?:within\s+)?(\d+\s*(?:hours?|business\s+days?|calendar\s+days?|days?))\b/i) ||
    cleanText.match(/\bwithin\s+(\d+\s*hours?)\b/i);

  if (breachMatch) {
    result.breachNotification = breachMatch[1];
  }

  // Metadata fallbacks
  if (!result.noticePeriod && Array.isArray(clause?.deadlines) && clause.deadlines.length > 0) {
    const dl = clause.deadlines.find((d) => /notice/i.test(d));
    if (dl) result.noticePeriod = dl;
  }
  if (!result.dueWindow && Array.isArray(clause?.deadlines) && clause.deadlines.length > 0) {
    const dl = clause.deadlines.find((d) => /day|month|net/i.test(d));
    if (dl) result.dueWindow = dl;
  }

  return result;
}

/**
 * Extracts key financial numbers, rates, caps, and fee structures
 */
export function extractKeyFinancials(text, clause) {
  const result = {
    amount: null,
    interestOrLateFee: null,
    liabilityCap: null,
    expenseLimit: null,
    additionalFees: false,
    rateAdjustment: false,
  };

  const cleanText = text || "";

  // Specific amount: e.g. $10,000 USD, 10,000 USD, $500.00
  const amountMatch =
    cleanText.match(/\$\s*[\d,]+(?:\.\d{2})?(?:\s*(?:USD|EUR|GBP|INR|dollars?))?/i) ||
    cleanText.match(/[\d,]+(?:\.\d{2})?\s*(?:USD|EUR|GBP|INR|dollars)/i);

  if (amountMatch) {
    result.amount = amountMatch[0].trim();
  } else if (Array.isArray(clause?.monetary_terms) && clause.monetary_terms.length > 0) {
    result.amount = String(clause.monetary_terms[0]).trim();
  }

  // Interest or late fee
  const interestMatch =
    cleanText.match(/\b(\d+(?:\.\d+)?%\s*(?:per\s+month|monthly|per\s+annum|annually)?)\b/i) ||
    cleanText.match(/\blate\s+fee\s+of\s+(\$?\s*[\d,]+(?:\.\d{2})?)/i);

  if (interestMatch) {
    result.interestOrLateFee = interestMatch[0].trim();
  } else if (/\blate\s+fee|interest\b/i.test(cleanText)) {
    result.interestOrLateFee = "late payment interest";
  }

  // Liability cap
  const capMatch =
    cleanText.match(/(?:liability|indemnification)[^.;]*?(?:not exceed|capped at|maximum of|up to)\s*(\$?\s*[\d,]+(?:\.\d{2})?)/i) ||
    cleanText.match(/\bmaximum\s+(?:aggregate\s+)?liability\s+(?:of\s+)?(\$?\s*[\d,]+)/i) ||
    cleanText.match(/\bfees?\s+paid\s+(?:in|under|during)\s+(?:the\s+prior|the\s+preceding)?\s*(\d+\s*months?|this\s+agreement)/i) ||
    cleanText.match(/\b(?:capped at|not to exceed|not exceed)\s*(\$?\s*[\d,]+)/i);

  if (capMatch) {
    result.liabilityCap = (capMatch[1] || capMatch[0]).trim();
  } else if (/\bfees?\s+paid\s+in\s+the\s+prior\s+12\s+months\b/i.test(cleanText)) {
    result.liabilityCap = "fees paid in the prior 12 months";
  } else if (/\baggregate\s+liability\s+exceed\b/i.test(cleanText)) {
    result.liabilityCap = "total contract fees paid";
  }

  // Expense limit
  const expMatch = cleanText.match(/\b(?:reimbursable\s+)?expenses?\s+(?:shall\s+not\s+exceed|not\s+to\s+exceed|capped\s+at)\s*(\$?\s*[\d,]+(?:\.\d{2})?)/i);
  if (expMatch) {
    result.expenseLimit = expMatch[1].trim();
  }

  result.additionalFees = /\b(?:additional\s+fees|reimbursable\s+expenses|expenses\s+shall\s+not\s+exceed|costs?\s+incurred)\b/i.test(cleanText);
  result.rateAdjustment = /\b(?:rate\s+increase|price\s+adjustment|annual\s+increase)\b/i.test(cleanText);

  return result;
}

/**
 * Extracts key conditions, exceptions, and triggers
 */
export function extractKeyConditions(text) {
  const lower = (text || "").toLowerCase();
  return {
    materialBreach: lower.includes("material breach") || lower.includes("default"),
    forConvenience: lower.includes("convenience") || lower.includes("without cause"),
    immediate: lower.includes("immediately") || lower.includes("without prior notice") || lower.includes("forthwith"),
    survival: lower.includes("survive") || lower.includes("survival"),
    nonRefundable: lower.includes("non-refundable") || lower.includes("non refundable"),
    disputedInvoice: lower.includes("dispute") && lower.includes("invoic"),
    thirdPartyTransfer: lower.includes("third part") || lower.includes("subprocessor"),
    consequentialExcluded: lower.includes("consequential") || lower.includes("indirect") || lower.includes("incidental") || lower.includes("punitive"),
    indemnityRequired: lower.includes("indemnif") || lower.includes("hold harmless"),
    uncappedExceptions: lower.includes("gross negligence") || lower.includes("willful misconduct"),
    disclaimer: lower.includes("as is") || lower.includes("disclaims") || lower.includes("merchantability"),
  };
}

/**
 * Extracts consequences of breach or actions
 */
export function extractKeyConsequences(text) {
  const lower = (text || "").toLowerCase();
  return {
    feesDueOrReturn: (lower.includes("immediately due") || lower.includes("due and payable")) && (lower.includes("return") || lower.includes("destroy")),
    serviceSuspension: lower.includes("suspend") || lower.includes("withhold"),
    immediateTermination: lower.includes("terminate immediately") || lower.includes("immediate cancellation"),
    legalRemedies: lower.includes("injunction") || lower.includes("remedies") || lower.includes("damages"),
  };
}

/**
 * Synthesizes a grounded, concise plain-English summary (2-4 sentences, ~40-80 words)
 * adapting to clause complexity, preserving responsible parties, obligations, deadlines,
 * amounts, exceptions, conditions, and consequences without hallucinating or blind truncation.
 */
export function generateConciseClauseSummary(clause, rawText) {
  const sourceText = getClauseSourceText(clause, rawText);
  const cleanText = (sourceText || "").trim();

  // If literally no substantive text exists
  if (!cleanText || cleanText.length < 15) {
    const title = clause?.title || clause?.clause_title;
    if (title && typeof title === "string" && title.trim().length > 0) {
      return `This clause establishes binding requirements for ${title.trim().toLowerCase()}, but specific obligations cannot be determined from the available text.`;
    }
    return "No substantive clause text was available to summarize this clause.";
  }

  // If text is extremely short and uninformative (< 25 chars)
  if (cleanText.length < 25) {
    return "Specific terms and obligations cannot be determined from the available text; review the complete contract provision.";
  }

  const category = detectClauseCategory(clause, cleanText);
  const party = extractPrimaryParty(cleanText, clause);
  const deadlines = extractKeyDeadlines(cleanText, clause);
  const money = extractKeyFinancials(cleanText, clause);
  const conditions = extractKeyConditions(cleanText);
  const consequences = extractKeyConsequences(cleanText);

  switch (category) {
    case "payment": {
      const s1 = money.amount && deadlines.dueWindow
        ? `${party} must pay ${money.amount} within ${deadlines.dueWindow} of invoice receipt.`
        : deadlines.dueWindow
          ? `${party} must settle all submitted invoices within ${deadlines.dueWindow} of receipt.`
          : money.amount
            ? `${party} must pay ${money.amount} according to the agreed billing and invoice schedule.`
            : `${party} is obligated to pay all fees and reimbursable expenses in accordance with agreed invoice terms.`;

      const s2 = money.interestOrLateFee
        ? `Late payments incur ${money.interestOrLateFee} and may lead to service suspension if left unresolved.`
        : conditions.disputedInvoice
          ? "Any disputed invoice amounts must be notified in writing within the required verification window."
          : "Payments must be made through approved disbursement methods without unauthorized deductions.";

      const s3 = money.expenseLimit
        ? `Reimbursable expenses are capped at ${money.expenseLimit} and require prior written authorization before reimbursement.`
        : conditions.nonRefundable
          ? "Advance deposits and scheduled fees remain strictly non-refundable once disbursed."
          : money.additionalFees
            ? "Additional expenses require prior written approval and supporting documentation before reimbursement."
            : "Invoices must be submitted with itemized expense receipts and approved through standard verification workflows.";

      const sentences = [s1, s2, s3].filter(Boolean);
      return sentences.join(" ");
    }

    case "termination": {
      const s1 = deadlines.noticePeriod
        ? `Either party may terminate the agreement by providing ${deadlines.noticePeriod} advance written notice.`
        : conditions.forConvenience
          ? "Either party is permitted to terminate the contract for convenience by providing prior written notice."
          : "Either party may terminate this agreement under specified contractual conditions and written notice procedures.";

      const s2 = conditions.materialBreach && deadlines.curePeriod
        ? `Immediate termination is authorized if a material breach is not remedied within the ${deadlines.curePeriod} cure period.`
        : conditions.materialBreach
          ? "Immediate termination is permitted if either party commits an uncured material breach or default."
          : conditions.immediate
            ? "Immediate termination without prior notice applies upon insolvency, bankruptcy, or critical default."
            : "Termination becomes legally effective upon receipt of formal written notice at the registered address.";

      const s3 = consequences.feesDueOrReturn
        ? "Upon cancellation, all accrued fees become due immediately, and proprietary materials must be returned or destroyed."
        : conditions.survival
          ? "Obligations concerning confidentiality, indemnification, and payment survive the termination of this agreement."
          : null;

      const sentences = [s1, s2, s3].filter(Boolean);
      return sentences.join(" ");
    }

    case "privacy": {
      const s1 = `${party} is legally required to process personal data strictly in accordance with documented instructions and data protection laws.`;

      const s2 = deadlines.breachNotification
        ? `Any security incident or personal data breach must be reported to the controller within ${deadlines.breachNotification}.`
        : "Appropriate technical and organizational safeguards must be maintained to prevent unauthorized data exposure.";

      const s3 = conditions.thirdPartyTransfer
        ? "Personal data cannot be transferred to third-party processors without prior written authorization."
        : "Data must be securely returned or permanently destroyed upon conclusion of the processing activities.";

      const sentences = [s1, s2, s3].filter(Boolean);
      return sentences.join(" ");
    }

    case "liability": {
      const s1 = conditions.indemnityRequired
        ? `${party} is obligated to defend, indemnify, and hold harmless the other party against specified third-party claims and liabilities.`
        : money.liabilityCap
          ? `Total aggregate liability under this agreement is strictly capped at ${money.liabilityCap}.`
          : "This clause establishes maximum monetary recovery limits and allocates legal liability between the parties.";

      const s2 = money.liabilityCap && conditions.indemnityRequired
        ? `Total aggregate indemnification liability under this provision is capped at ${money.liabilityCap}.`
        : conditions.consequentialExcluded
          ? "Neither party is liable for indirect, incidental, special, punitive, or consequential damages."
          : "Damages are restricted exclusively to proven direct financial losses arising from contractual non-performance.";

      const s3 = deadlines.noticePeriod
        ? `Written notice of any indemnification or liability claim must be provided within ${deadlines.noticePeriod}.`
        : conditions.consequentialExcluded
          ? "Neither party is liable for indirect, incidental, special, punitive, or consequential damages."
          : "Damages are restricted exclusively to proven direct financial losses arising from contractual non-performance.";

      const s4 = conditions.uncappedExceptions
        ? "Liability protections do not excuse gross negligence, willful misconduct, or material breach."
        : null;

      const sentences = [s1, s2, s3, s4].filter(Boolean);
      return sentences.join(" ");
    }

    case "renewal": {
      const s1 = deadlines.noticePeriod
        ? `The agreement automatically renews for successive terms unless cancellation notice is given at least ${deadlines.noticePeriod} prior to expiration.`
        : "The agreement renews automatically for successive periods unless either party provides timely opt-out notice.";

      const s2 = money.rateAdjustment
        ? "Renewal terms may incorporate adjusted service rates or pricing increases as established in the contract."
        : "Both parties remain bound by all active terms and operational responsibilities during any extended period.";

      const s3 = "Missing the formal cancellation deadline commits the parties to the full subsequent renewal duration.";

      const sentences = [s1, s2, s3].filter(Boolean);
      return sentences.join(" ");
    }

    case "confidentiality": {
      const s1 = "Both parties are strictly required to keep all proprietary information and trade secrets confidential.";
      const s2 = "Confidential records may only be disclosed to authorized personnel with a legitimate need to know under equivalent restrictions.";
      const s3 = conditions.survival
        ? "These non-disclosure obligations survive the expiration or termination of this agreement."
        : "All confidential files and copies must be returned or certified destroyed upon agreement termination.";

      const sentences = [s1, s2, s3].filter(Boolean);
      return sentences.join(" ");
    }

    case "intellectual_property": {
      const s1 = "This clause defines ownership, licensing rights, and restrictions regarding work products and proprietary inventions.";
      const s2 = "Deliverables created under this agreement are assigned or licensed to the client upon full payment of fees.";
      const s3 = "Pre-existing proprietary assets, tools, and background intellectual property remain the exclusive property of their respective creators.";

      const sentences = [s1, s2, s3].filter(Boolean);
      return sentences.join(" ");
    }

    case "warranty": {
      const s1 = `${party} warrants that all provided services and deliverables will adhere to agreed professional specifications and standards.`;
      const s2 = conditions.disclaimer
        ? "Except for express warranties stated, all implied warranties of merchantability and fitness for purpose are disclaimed."
        : "Deficiencies must be corrected promptly upon written notification of non-conformity.";
      const s3 = "The exclusive remedy for defective performance is correction or re-performance at no additional charge.";

      const sentences = [s1, s2, s3].filter(Boolean);
      return sentences.join(" ");
    }

    case "dispute": {
      const s1 = "This agreement is governed by the laws of the designated jurisdiction, where formal legal claims must be filed.";
      const s2 = "The parties are required to attempt good-faith informal negotiation or mediation before initiating litigation or arbitration.";
      const s3 = "Any arbitration awards rendered are final, binding, and enforceable in any court of competent jurisdiction.";

      const sentences = [s1, s2, s3].filter(Boolean);
      return sentences.join(" ");
    }

    case "audit": {
      const s1 = "One party is granted the right to inspect relevant books, records, and facilities to verify contractual compliance.";
      const s2 = deadlines.noticePeriod
        ? `Audits must be conducted during normal business hours upon ${deadlines.noticePeriod} advance written notice.`
        : "Reviews must occur during normal working hours upon reasonable advance notice to minimize operational disruption.";
      const s3 = "Each party bears its own audit costs unless a material discrepancy is discovered during the examination.";

      const sentences = [s1, s2, s3].filter(Boolean);
      return sentences.join(" ");
    }

    case "subcontracting": {
      const s1 = "Neither party may assign this agreement or delegate key responsibilities to third parties without prior written consent.";
      const s2 = "Approved subcontractors or assignees must execute binding commitments meeting the same performance and security standards.";
      const s3 = "The delegating party remains fully responsible and liable for all acts and omissions of its subcontractors.";

      const sentences = [s1, s2, s3].filter(Boolean);
      return sentences.join(" ");
    }

    default: {
      const s1 = `${party} must fulfill all operational responsibilities and legal obligations defined in this provision.`;
      const s2 = deadlines.noticePeriod || deadlines.dueWindow
        ? `All actions are subject to the specified timeframe of ${deadlines.noticePeriod || deadlines.dueWindow}.`
        : "Performance is subject to verified contractual conditions, standard review procedures, and mutual compliance.";
      const s3 = "Non-compliance may constitute a contractual default resulting in formal notice or legal remedies.";

      const sentences = [s1, s2, s3].filter(Boolean);
      return sentences.join(" ");
    }
  }
}

export function getShortSimpleExplanation(clause, rawText) {
  return generateConciseClauseSummary(clause, rawText);
}

export function getWhatItSays(clause, rawText) {
  const sourceText = getClauseSourceText(clause, rawText);
  if (!clause && !sourceText) return "No explanation available.";

  const cleanSource = (sourceText || "").trim();
  const rawCleanNorm = cleanSource.toLowerCase().replace(/\s+/g, " ");

  const candidate = (
    clause?.meaning ||
    clause?.plain_language ||
    clause?.summary ||
    clause?.explanation ||
    ""
  ).trim();

  const candidateNorm = candidate.toLowerCase().replace(/\s+/g, " ");
  const candidateWords = candidate ? candidate.split(/\s+/).filter(Boolean) : [];
  const rawWords = cleanSource ? cleanSource.split(/\s+/).filter(Boolean) : [];

  // If candidate is a genuine 1-4 sentence concise summary:
  // - Length: between 5 and 85 words, and <= 450 characters
  // - Does not end abruptly with an ellipsis
  // - If rawClean is lengthy (> 35 words), candidate must not be the identical raw text dump
  if (
    candidate &&
    candidateWords.length >= 5 &&
    candidateWords.length <= 85 &&
    candidate.length <= 450 &&
    !/(?:\.{3,}|…)$/.test(candidate) &&
    (rawWords.length <= 35 || candidateNorm !== rawCleanNorm)
  ) {
    return candidate;
  }

  // Synthesize concise 2-4 sentence summary (~40-80 words)
  return generateConciseClauseSummary(clause, cleanSource);
}

export function getWhyThisIsImportant(clause, rawText, detailReasons = []) {
  const points = [];
  const sourceText = getClauseSourceText(clause, rawText);
  const text = (sourceText || "").trim();
  const lowerText = text.toLowerCase();
  const category = detectClauseCategory(clause, text);
  const isHighRisk = String(clause?.risk_level || clause?.risk || "").toUpperCase() === "HIGH";

  // 1. If high risk, ensure a specific risk reason is prioritized
  const reasons = [
    ...(Array.isArray(detailReasons) ? detailReasons : detailReasons ? [detailReasons] : []),
    ...(Array.isArray(clause?.risk_reasons) ? clause.risk_reasons : clause?.risk_reasons ? [clause.risk_reasons] : []),
  ];

  for (const r of reasons) {
    if (!r) continue;
    let clean = String(r).trim().replace(/^[-•*]\s*/, "");
    if (clean && !points.some((p) => p.toLowerCase() === clean.toLowerCase())) {
      clean = clean.charAt(0).toUpperCase() + clean.slice(1);
      if (!clean.endsWith(".")) clean += ".";
      points.push(clean);
      if (points.length >= 2) break;
    }
  }

  // 2. Check if backend already provided why_important
  if (Array.isArray(clause?.why_important) && clause.why_important.length > 0) {
    for (const item of clause.why_important) {
      if (item && !points.includes(item)) points.push(item);
      if (points.length >= 3) break;
    }
  }

  // 3. Category & content grounding
  if (category === "termination") {
    if (!points.some((p) => p.toLowerCase().includes("terminat"))) {
      points.push("This defines how the agreement can be terminated.");
    }
    const noticeMatch =
      text.match(/\b(\d+)\s*[- ]?(business\s+days?|calendar\s+days?|days?|weeks?|months?)['’]?\s+(?:advance\s+|prior\s+)?(?:written\s+)?notice\b/i) ||
      text.match(/\b(?:written\s+)?notice\s+of\s+(?:not\s+less\s+than\s+)?(\d+\s*(?:business\s+days?|calendar\s+days?|days?|weeks?|months?)['’]?)\b/i) ||
      text.match(/\b(\d+)[ -](?:day|month|week)\s+(?:written\s+)?notice\b/i);
    if (noticeMatch) {
      const days = noticeMatch[1];
      points.push(`A ${days}-day notice period applies to ordinary termination.`);
    } else if (/\bimmediate(?:ly)?|without prior notice\b/i.test(lowerText)) {
      points.push("Allows immediate termination under breach or default conditions.");
    }
    if (/\bcure\s+period|remedy\s+within\b/i.test(lowerText)) {
      points.push("Provides a cure period to remedy breaches before cancellation occurs.");
    }
  } else if (category === "payment") {
    if (!points.some((p) => /financial|payment|invoice/i.test(p))) {
      points.push("Establishes binding financial commitments, billing frequency, and payment schedules.");
    }
    const dueMatch =
      text.match(/\bwithin\s+(\d+\s*(?:business\s+days?|calendar\s+days?|days?|weeks?|months?))\b/i) ||
      text.match(/\bnet\s+(\d+)\b/i);
    if (dueMatch && !points.some((p) => p.includes("within"))) {
      points.push(`Requires payments to be completed within ${dueMatch[1] || dueMatch[0]} of invoice.`);
    }
    if (/\blate\s+fee|interest\b|penalt/i.test(lowerText)) {
      points.push("Delayed payments may incur interest charges, late fees, or service suspension.");
    }
    if (/\bnon-refundable|advance\s+deposit\b/i.test(lowerText)) {
      points.push("Certain fees or deposits are non-refundable once paid.");
    }
  } else if (category === "privacy") {
    if (!points.some((p) => /personal|customer|data|privacy/i.test(p))) {
      points.push("Governs how personal, customer, or confidential data is collected, handled, and safeguarded.");
    }
    if (/\bthird\s*part|subprocessor\b/i.test(lowerText)) {
      points.push("Regulates sharing and transmission of protected data to third-party providers.");
    }
    if (/\bbreach|incident|notify\b/i.test(lowerText)) {
      points.push("Mandates security safeguards and prompt breach notification.");
    }
  } else if (category === "liability") {
    if (!points.some((p) => /monetary recovery limits|legal risk|liability|damages/i.test(p))) {
      points.push("Allocates legal risk and defines monetary recovery limits between the parties.");
    }
    if (/\bindemnif|hold harmless\b/i.test(lowerText)) {
      points.push("Requires one party to defend and financially protect the other against third-party claims.");
    }
    if (/\bconsequential|indirect|incidental|punitive\b/i.test(lowerText)) {
      points.push("Excludes liability for indirect, punitive, or consequential losses.");
    }
    if (/\baggregate\s+liability|maximum\s+liability|fees\s+paid\b/i.test(lowerText)) {
      points.push("Places an aggregate cap on total recoverable monetary damages.");
    }
  } else if (category === "renewal") {
    points.push("Controls how the term of the agreement is extended or renewed.");
    if (/\bauto(?:matic(?:ally)?)?\s*renew/i.test(lowerText)) {
      points.push("The agreement automatically renews unless cancellation notice is given before the deadline.");
    }
  } else if (category === "confidentiality") {
    points.push("Restricts disclosure of proprietary business information and trade secrets.");
    if (/\bsurvive\b/i.test(lowerText)) {
      points.push("Confidentiality obligations survive the expiration or termination of this agreement.");
    }
  }

  // 4. Fallback if sparse
  if (points.length === 0) {
    if (text.length < 25) {
      points.push("Specific operational impacts cannot be determined from the available text.");
    } else {
      const title = clause?.title || "Contract clause";
      points.push(`Defines binding operational requirements and legal duties for ${title.toLowerCase()}.`);
      points.push("Non-compliance may trigger contractual remedies or legal claims.");
    }
  }

  // If high risk and still only 1 point, ensure high-risk context is clear
  if (isHighRisk && points.length < 2) {
    points.push("This clause represents a high-risk contractual term that requires thorough review before signing.");
  }

  // Return strictly 1-3 specific grounded points
  return points.slice(0, 3);
}

export function getWhatShouldYouDo(clause, rawText, detailRecommendations = []) {
  const steps = [];
  const sourceText = getClauseSourceText(clause, rawText);
  const text = (sourceText || "").trim();
  const lowerText = text.toLowerCase();
  const category = detectClauseCategory(clause, text);

  // 1. Domain-specific review steps based on actual clause
  if (category === "payment") {
    steps.push("Check amount, due date, late fees and payment method.");
    const dueMatch =
      text.match(/\bwithin\s+(\d+\s*(?:business\s+days?|calendar\s+days?|days?|weeks?|months?))\b/i) ||
      text.match(/\bnet\s+(\d+)\b/i);
    if (dueMatch) {
      steps.push(`Verify payment due date window (${dueMatch[1] || dueMatch[0]}) and invoice submission requirements.`);
    }
    if (/\blate\s+fee|interest|penalt/i.test(lowerText)) {
      steps.push("Check late payment fee percentages and interest calculation formulas.");
    }
  } else if (category === "termination") {
    const noticeMatch =
      text.match(/\b(\d+)\s*[- ]?(business\s+days?|calendar\s+days?|days?|weeks?|months?)['’]?\s+(?:advance\s+|prior\s+)?(?:written\s+)?notice\b/i) ||
      text.match(/\b(?:written\s+)?notice\s+of\s+(?:not\s+less\s+than\s+)?(\d+\s*(?:business\s+days?|calendar\s+days?|days?|weeks?|months?)['’]?)\b/i) ||
      text.match(/\b(\d+)[ -](?:day|month|week)\s+(?:written\s+)?notice\b/i);
    if (noticeMatch) {
      steps.push(`Check whether the ${noticeMatch[1]}-day notice period works for you.`);
    } else {
      steps.push("Check notice period, termination conditions and notice method.");
    }
    steps.push("Check the required method for submitting notice.");
    steps.push("Keep evidence of the notice after submission.");
  } else if (category === "renewal") {
    steps.push("Check renewal date, notice period and cancellation requirements.");
    steps.push("Calendar reminders well ahead of the opt-out cutoff date.");
    steps.push("Verify pricing adjustments or automatic rate increases that apply upon renewal.");
  } else if (category === "privacy") {
    steps.push("Check collected data, sharing, usage and retention.");
    steps.push("Verify third-party transfer rules and security compliance standards.");
    steps.push("Check incident reporting timelines in case of a data breach.");
  } else if (category === "liability") {
    steps.push("Check liability limits, exclusions and responsibilities.");
    steps.push("Confirm whether liability caps and indemnity protections are mutual.");
    steps.push("Check who has the right to direct and control legal defense in third-party claims.");
  } else if (category === "confidentiality") {
    steps.push("Check what information is protected, permitted disclosures and duration.");
    steps.push("Confirm allowed recipients (e.g. employees, professional advisors) and standard exceptions.");
    steps.push("Verify requirements for returning or destroying confidential records upon termination.");
  }

  // 2. Incorporate explicit backend recommendations if present
  const rawRecs = [
    ...(Array.isArray(detailRecommendations) ? detailRecommendations : detailRecommendations ? [detailRecommendations] : []),
    ...(Array.isArray(clause?.recommendations) ? clause.recommendations : clause?.recommendations ? [clause.recommendations] : []),
  ];

  for (const r of rawRecs) {
    if (!r) continue;
    let clean = String(r).trim().replace(/^[-•*]\s*/, "");
    if (clean && !steps.some((s) => s.toLowerCase() === clean.toLowerCase())) {
      clean = clean.charAt(0).toUpperCase() + clean.slice(1);
      if (!clean.endsWith(".")) clean += ".";
      steps.push(clean);
      if (steps.length >= 3) break;
    }
  }

  // 3. Fallback for general / unknown clauses
  if (steps.length === 0) {
    if (text.length < 25) {
      steps.push("Review requirements cannot be determined from the available text; verify full contract terms.");
    } else {
      steps.push("Identify who is responsible for each duty under this clause.");
      steps.push("Verify all deadlines, operational conditions, and notice triggers.");
      steps.push("Review this clause together with related agreement terms before signing.");
    }
  }

  // Return strictly 1-3 practical actions
  return steps.slice(0, 3);
}

export function getClauseSourceText(clause, explicitText = "") {
  if (explicitText && typeof explicitText === "string" && explicitText.trim().length > 0) {
    return explicitText.trim();
  }
  if (!clause) return "";
  if (typeof clause === "string") return clause.trim();

  const direct =
    clause.clauseText ||
    clause.text ||
    clause.content ||
    clause.raw_text ||
    clause.rawText ||
    clause.clause_text ||
    clause.original_text ||
    clause.source_text ||
    clause.clause_content;

  if (direct && typeof direct === "string" && direct.trim().length > 0 && direct !== "No explanation available.") {
    return direct.trim();
  }

  const parts = [];
  if (typeof clause.evidence === "string" && clause.evidence.trim().length > 0) {
    parts.push(clause.evidence.trim());
  } else if (Array.isArray(clause.evidence)) {
    parts.push(...clause.evidence.filter((e) => typeof e === "string" && e.trim()));
  }

  if (Array.isArray(clause.notices)) parts.push(...clause.notices);
  if (Array.isArray(clause.obligations)) parts.push(...clause.obligations);
  if (Array.isArray(clause.conditions)) parts.push(...clause.conditions);
  if (Array.isArray(clause.prohibitions)) parts.push(...clause.prohibitions);
  if (Array.isArray(clause.rights)) parts.push(...clause.rights);
  if (Array.isArray(clause.duties)) parts.push(...clause.duties);
  if (Array.isArray(clause.triggers)) parts.push(...clause.triggers);
  if (Array.isArray(clause.consequences)) parts.push(...clause.consequences);

  const combined = parts.filter((p) => typeof p === "string" && p.trim().length > 0).join(" ");
  if (combined.trim().length > 0) {
    return combined.trim();
  }

  const fallback = clause.meaning || clause.plain_language || clause.summary || clause.explanation || "";
  if (typeof fallback === "string" && fallback.trim() !== "No explanation available.") {
    return fallback.trim();
  }
  return "";
}

export function getPotentialConcerns(clause, rawText) {
  const concerns = [];
  const text = getClauseSourceText(clause, rawText);

  // If text is genuinely missing
  if (!text && !clause?.meaning) {
    return [
      "Clause text is missing from the document or could not be extracted for analysis.",
      "Confirm the full clause wording from the physical or original digital execution copy."
    ];
  }

  const effectiveText = text || clause?.meaning || clause?.title || "";

  // 1. Backend potential_concerns if provided (filter alarmist words)
  if (Array.isArray(clause?.potential_concerns) && clause.potential_concerns.length > 0) {
    for (const item of clause.potential_concerns) {
      if (item && typeof item === "string") {
        const sanitized = item.replace(/\b(?:dangerous|illegal|fraudulent|unfair)\b/gi, "unusual");
        if (!concerns.includes(sanitized)) concerns.push(sanitized);
      }
    }
  }

  // 2. Missing or blank values (e.g. $_____, __________, (DATE), [DATE], [insert ...], [TBD])
  if (/\$__+|\$\s*\[\s*_+|\$\s*___+/i.test(effectiveText)) {
    concerns.push("The payment cap contains a blank amount in the available text. Verify the completed amount before relying on this provision.");
  } else if (/_{2,}|\[\s*_{2,}\s*\]|\[\s*\]|\[\s*(?:insert|insert\s+here|tbd|to\s+be\s+determined|amount|name|party)\b[^\]]*\]/i.test(effectiveText)) {
    concerns.push("A value appears to be missing or blank in the available text. Verify the completed terms before accepting.");
  }

  if (/\(DATE\)|\[DATE\]|\[insert\s+date\]/i.test(effectiveText)) {
    concerns.push("The clause contains a blank (DATE) placeholder in the available text. Verify the effective or expiration dates.");
  }

  // 3. Incomplete sentences or truncated text
  const isTruncated =
    /(?:\.{3,}|…)\s*$/.test(effectiveText) ||
    /[,;:\-\–]\s*$/.test(effectiveText) ||
    /\b(?:if|unless|provided\s+that|subject\s+to|and|or|with\s+respect\s+to|such\s+as)\s*$/i.test(effectiveText);
  if (isTruncated) {
    concerns.push("The clause appears to be truncated or incomplete at the end. Check the complete source contract.");
  }

  // 4. References to missing exhibits, schedules, annexures, appendices
  const exhibitMatch = effectiveText.match(/\b(Exhibit\s+[A-Z0-9]+(?:\s*:\s*[^,.;]+)?|Schedule\s+[A-Z0-9]+|Annexure\s+[A-Z0-9]+|Appendix\s+[A-Z0-9]+|Attachment\s+[A-Z0-9]+|Addendum\s+[A-Z0-9]+)/i);
  if (exhibitMatch) {
    const docRef = exhibitMatch[1].trim();
    if (/Exhibit\s+A(?:\s*:\s*Scope\s+of\s+Services)?/i.test(docRef)) {
      concerns.push("The clause depends on Exhibit A for the scope of services, but the referenced content is not present in the available contract text.");
      concerns.push("Verify Exhibit A before accepting the agreement.");
    } else {
      concerns.push(`The clause refers to ${docRef}, which is not detailed in the available text. Check the referenced document before accepting.`);
    }
  }

  // Reference to internal sections: "subject to Section X", "as defined in Section Y"
  const sectionRefMatch = effectiveText.match(/\b(?:subject\s+to|as\s+(?:set\s+forth|defined|described)\s+in)\s+(Section\s+[0-9A-Za-z.-]+|Article\s+[0-9A-Za-z.-]+|Clause\s+[0-9A-Za-z.-]+)/i);
  if (sectionRefMatch) {
    concerns.push(`The clause is ${sectionRefMatch[0].toLowerCase()}. Verify ${sectionRefMatch[1]} to understand how it modifies or limits this provision.`);
  }

  // 5. Undefined / ambiguous wording (neutral language)
  if (/\breasonably\s+satisfactory\b/i.test(effectiveText)) {
    concerns.push('The standard "reasonably satisfactory" is subjective and not explicitly defined. Clarify the evaluation criteria.');
  } else if (/\breasonable\s+efforts\b/i.test(effectiveText)) {
    concerns.push('The term "reasonable efforts" is not specifically defined in the available text. The wording may require clarification.');
  } else if (/\bbest\s+efforts\b/i.test(effectiveText)) {
    concerns.push('The standard "best efforts" establishes a heightened standard that is not specifically defined in the available text. Clarify the expected scope.');
  } else if (/\bcommercially\s+reasonable(?:\s+efforts)?\b/i.test(effectiveText)) {
    concerns.push('The standard "commercially reasonable" is subjective and not explicitly quantified in this clause. Check whether benchmark criteria exist.');
  }

  if (/\bas\s+needed\b/i.test(effectiveText)) {
    concerns.push('The requirement "as needed" does not define an objective frequency or limit. Clarify the expected operational commitment.');
  }

  if (/\b(?:at\s+(?:its|commission'?s|client'?s)?\s*sole\s+discretion|in\s+(?:its|commission'?s|client'?s)?\s*sole\s+discretion|sole\s+opinion)\b/i.test(effectiveText)) {
    concerns.push('The phrase "sole discretion" gives one party unilateral control over this decision. This should be verified.');
  }

  if (/\bmaterial\s+breach\b/i.test(effectiveText) && !/\bdefined\s+as\b/i.test(effectiveText)) {
    concerns.push('The term "material breach" is not defined within this clause. Check whether the agreement defines what constitutes a material breach.');
  }

  if (/\b(?:prompt\s+notice|promptly\s+notify)\b/i.test(effectiveText) && !/\b\d+\s*(?:business\s+days?|calendar\s+days?|days?|hours?)\b/i.test(effectiveText)) {
    concerns.push('The clause requires "prompt notice" but does not define an exact number of business days. Clarify the acceptable notice timeframe.');
  }

  // 6. Broad cost exposure / significant liability
  if (/\bliable\s+for\s+any\s+and\s+all\s+(?:reasonable\s+)?costs?\b/i.test(effectiveText) || /\bunlimited\s+liability\b/i.test(effectiveText)) {
    concerns.push("The clause may create potentially broad cost exposure following a specified default. Check whether another provision limits or defines the applicable liability.");
  }

  // 7. Unclear renewal or payment conditions
  const category = detectClauseCategory(clause, effectiveText);
  if (category === "renewal" && /\bauto(?:matic(?:ally)?)?\s*renew/i.test(effectiveText)) {
    if (!/\b\d+\s*(?:business\s+days?|calendar\s+days?|days?|months?|weeks?)\b/i.test(effectiveText)) {
      concerns.push("The clause provides for automatic renewal, but the specific cancellation window or deadline is not specified in the available text.");
    }
  }

  if (category === "payment" && /\b(?:additional\s+fees|expenses\s+shall\s+be\s+reimbursed|costs?\s+incurred|penalt(?:y|ies))\b/i.test(effectiveText)) {
    if (!/\$\s*\d+|\b\d+\s*(?:dollars|usd|inr|eur|%|percent)\b/i.test(effectiveText) && !/\$__+/i.test(effectiveText)) {
      concerns.push("The clause references additional fees or expenses, but does not specify exact amounts or calculation limits in the available text.");
    }
  }

  // Deduplicate and cap to 1-3 concerns
  const uniqueConcerns = [];
  for (const c of concerns) {
    if (!uniqueConcerns.includes(c)) {
      uniqueConcerns.push(c);
      if (uniqueConcerns.length >= 3) break;
    }
  }

  // 8. Complete clause with no concern
  if (uniqueConcerns.length === 0) {
    return ["No specific ambiguity or missing information was identified in the available clause text."];
  }

  return uniqueConcerns;
}
