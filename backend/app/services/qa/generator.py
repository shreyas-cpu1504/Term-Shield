from __future__ import annotations

import re
from app.services.gemini_service import GeminiService
from app.services.retrieval_service import RetrievedClause
from app.services.qa.analyzer import QuestionAnalysis
from app.services.qa.integrity import EvidenceIntegrityChecker


class AnswerGenerator:
    """
    Unified Gemini Prompt and Answer Generator for Ask My T&C.
    One single prompt architecture for all question types and languages.
    """

    @classmethod
    def generate(
        cls,
        analysis: QuestionAnalysis,
        evidence: list[RetrievedClause],
        conversation_context: str,
        contract_name: str | None = None,
        contract_summary: str | None = None,
    ) -> str:
        # Check for conversational / capability / unrelated shortcuts
        if analysis.coarse_intent == "general":
            return cls._handle_general_conversational(analysis.cleaned_question, analysis.language)
        if analysis.coarse_intent == "capability":
            return cls._handle_capability(analysis.cleaned_question, analysis.language)
        if analysis.coarse_intent == "unrelated":
            return cls._handle_unrelated(analysis.cleaned_question, analysis.language)

        # Build evidence context block
        evidence_blocks: list[str] = []
        truncated_warnings: list[str] = []

        for item in evidence:
            label = item.title or (f"Clause {item.clause_number}" if item.clause_number else "Contract Section")
            if item.clause_number and item.title and not item.title.lower().startswith(f"clause {item.clause_number}"):
                label = f"Clause {item.clause_number}: {item.title}"

            text = (item.text or "").strip()
            if not text:
                continue

            integrity = EvidenceIntegrityChecker.check_clause_text(text)
            if integrity.is_truncated:
                label += f" [WARNING: INCOMPLETE TEXT - ENDS AT '{integrity.truncated_fragment}']"
                text = f"{text} [TEXT ENDS ABRUPTLY HERE AT '{integrity.truncated_fragment}']"
                truncated_warnings.append(
                    f"{label}: The extracted text ends abruptly at '{integrity.truncated_fragment}'. "
                    f"Confirmed portion: '{integrity.confirmed_portion}'."
                )

            evidence_blocks.append(f"[{label}]\n{text}")

        evidence_str = "\n\n".join(evidence_blocks) if evidence_blocks else "No matching contract evidence found."

        # Metadata header
        meta_lines: list[str] = []
        if contract_name:
            meta_lines.append(f"Contract Document: {contract_name}")
        if contract_summary:
            meta_lines.append(f"Contract Overview: {contract_summary}")
        meta_header = ("\n".join(meta_lines) + "\n\n") if meta_lines else ""

        # Language Mandate
        target_lang = analysis.language or "English"
        if target_lang.lower() == "english":
            lang_mandate = (
                "OUTPUT LANGUAGE MANDATE: You MUST answer strictly in English. "
                "Do NOT use Telugu, Hindi, or any other regional script unless explicitly instructed."
            )
        else:
            lang_mandate = (
                f"OUTPUT LANGUAGE MANDATE: You MUST write your ENTIRE response in {target_lang} using proper {target_lang} script. "
                f"Do NOT answer in English. Translate and explain the contract terms naturally into {target_lang} while preserving accurate legal meaning."
            )

        # Truncation instructions
        integrity_prompt_section = ""
        if truncated_warnings:
            integrity_prompt_section = (
                "\nCRITICAL SOURCE TRUNCATION NOTICE:\n"
                + "\n".join(f"- {w}" for w in truncated_warnings)
                + "\nCRITICAL TRUNCATION RULES:\n"
                "1. You MUST explain the confirmed portion of the clause naturally and helpfully.\n"
                "2. You MUST explicitly state that the available extracted text ends abruptly at the indicated letters/words, so the exact notice period or full terms cannot be confirmed.\n"
                "3. You must NEVER invent, assume, or autocomplete the cut-off text (for example, if the text ends at '30 da', you must NEVER claim or write '30 days').\n"
            )

        # Formatting guidance based on user's fine intent
        format_guidance = ""
        if analysis.fine_intent == "simplification":
            format_guidance = (
                "INTENT: SIMPLIFICATION\n"
                "Explain the referenced clause or contract terms in extremely simple, plain, conversational language. "
                "Do NOT just copy or repeat the raw legal text; explain what it actually means in plain terms that anyone can understand."
            )
        elif analysis.fine_intent == "translation":
            format_guidance = (
                f"INTENT: TRANSLATION & EXPLANATION IN {target_lang.upper()}\n"
                f"Provide a natural, complete explanation and translation of the referenced clause in {target_lang}. "
                f"Explain the meaning clearly in {target_lang} so the user understands their rights, duties, and deadlines."
            )
        elif analysis.fine_intent == "obligation":
            format_guidance = (
                "INTENT: OBLIGATIONS & ACTION ITEMS\n"
                "Clearly explain what the user or party is REQUIRED TO DO. Break down specific action items, conditions, "
                "notice requirements, and due dates based strictly on the verified evidence."
            )
        elif analysis.fine_intent == "penalty":
            format_guidance = (
                "INTENT: CONSEQUENCES & IF YOU DON'T DO IT\n"
                "Clearly explain what happens if a party fails to take action, fails to give notice, or breaches the terms. "
                "Highlight the specific consequences, penalties, automatic extensions, or remedies stated in the evidence."
            )
        elif analysis.fine_intent == "risk":
            format_guidance = (
                "INTENT: RISK ANALYSIS\n"
                "Highlight the potential legal, operational, or financial risks under the clause/contract (e.g. automatic renewal, "
                "unlimited liability, forfeiture) and explain why it matters to the user."
            )
        elif analysis.fine_intent == "deadline":
            format_guidance = (
                "INTENT: DEADLINES & NOTICE PERIODS\n"
                "Highlight the specific time limits, notice periods, due dates, and timelines stated in the evidence."
            )
        elif analysis.fine_intent == "responsibility":
            format_guidance = (
                "INTENT: RESPONSIBILITY & LIABILITY\n"
                "Clarify which party is responsible, who bears liability, and who must pay or perform."
            )
        elif analysis.clause_number or analysis.fine_intent == "exact_clause":
            clause_num = analysis.clause_number or ""
            if target_lang.lower() == "telugu":
                format_guidance = f"""FORMAT REQUIREMENT FOR CLAUSE EXPLANATION (TELUGU):
Structure the explanation clearly with these exact sections:
### క్లాజ్ {clause_num} — [Title]

**క్లాజ్ ఏమి చెబుతోంది**
[Accurate summary of verified text]

**సింపుల్గా అర్థం**
[Plain language explanation for ordinary readers]

**ముఖ్యమైన విషయం**
[Key point or risk]

**మీరు చేయాల్సింది**
[Action point or requirement]

**Source: Clause {clause_num}**"""
            elif target_lang.lower() == "hindi":
                format_guidance = f"""FORMAT REQUIREMENT FOR CLAUSE EXPLANATION (HINDI):
Structure the explanation clearly with these exact sections:
### खंड {clause_num} — [Title]

**शर्त क्या कहती है**
[Accurate summary of verified text]

**आसान शब्दों में मतलब**
[Plain language explanation]

**महत्वपूर्ण बात**
[Key point or risk]

**आपको क्या करना होगा**
[Action point or requirement]

**Source: Clause {clause_num}**"""
            else:
                format_guidance = f"""FORMAT REQUIREMENT FOR CLAUSE EXPLANATION:
Structure the explanation clearly with these 4 distinct sections:
### Clause {clause_num} — [Title]

**What it says**
[Accurate summary of verified text. Quote or preserve key exact duties, conditions, and amounts such as 'exercise special skill' or 'DUTIES']

**In simple terms**
[Plain language explanation for non-lawyers. Clearly state what services are provided, payment terms, and consequences in simple bullet points]

**Important point**
[Key point, legal significance, or potential risk]

**What you may need to do**
[Action point, compliance duty, or practical step]

**Source: Clause {clause_num}**"""

        prompt = f"""You are Term Shield's expert contract AI assistant. You answer questions about contracts accurately, clearly, and naturally like an intelligent conversational assistant (like ChatGPT) grounded strictly in verified contract evidence.

{meta_header}{conversation_context}CONTRACT EVIDENCE:
{evidence_str}
{integrity_prompt_section}
{lang_mandate}

CORE RULES:
1. Grounding: Answer ONLY using verified contract evidence. Never invent, extrapolate, or assume terms, deadlines, or fees not present in the evidence.
2. Incomplete Source: If contract evidence ends abruptly (e.g. at '30 da'):
   - Explain the confirmed portion clearly.
   - Explicitly inform the user that the source text ends at that point, so the exact terms cannot be confirmed.
   - NEVER invent or autocomplete the cut-off words (e.g. never change '30 da' to '30 days').
3. Multi-turn Follow-ups: If the user's question refers to previous turns ('in Telugu', 'make it simple', 'what do I need to do?', 'what is the risk?'), maintain continuity and answer for the referenced clause or topic.
4. Conversational Tone: Be helpful, objective, and natural. Do NOT output raw clauses without explanation. Explain the legal significance clearly.

{format_guidance}

USER QUESTION:
{analysis.cleaned_question}

ANSWER:"""

        return GeminiService.generate(prompt)

    @classmethod
    def _handle_general_conversational(cls, question: str, language: str) -> str:
        q_low = question.lower()
        if any(w in q_low for w in ["do u know me", "do you know me", "who am i"]):
            return (
                "I don't have access to your personal information unless you provide it. "
                "I'm mainly here to help you understand your contracts, explain clauses, highlight obligations, check deadlines, and point out potential risks."
            )

        if any(w in q_low for w in ["who are you", "who r u"]):
            if language == "Telugu":
                return "నమస్కారం! నేను Term Shield కాంట్రాక్ట్ AI అసిస్టెంట్‌ని. మీ ఒప్పంద నిబంధనలు, బాధ్యతలు మరియు రిస్క్‌లను అర్థం చేసుకోవడంలో నేను మీకు సహాయపడతాను."
            elif language == "Hindi":
                return "नमस्ते! मैं Term Shield अनुबंध AI सहायक हूँ। मैं आपके अनुबंध की शर्तों, दायित्वों اور जोखिमों को समझने में आपकी सहायता करता हूँ।"
            return "I am Term Shield, your contract analysis AI assistant. I help you review agreements, understand complex clauses, identify obligations, and spot potential risks."

        if "what is a contract" in q_low:
            return "A contract is a legally binding agreement between two or more parties that defines their mutual rights, obligations, and terms of performance enforceable by law."
        if "nda" in q_low:
            return "An NDA (Non-Disclosure Agreement) is a legally binding contract where parties agree not to disclose confidential or proprietary information shared with each other."
        if "sla" in q_low:
            return "An SLA (Service Level Agreement) defines the level of service, standards, and performance metrics expected between a service provider and a customer."
        if "term shield" in q_low:
            return "Term Shield is an AI-powered legal contract analysis platform designed to help you understand complex agreements, highlight obligations, uncover risks, and explain terms in plain language."

        if any(w in q_low for w in ["how do you work", "how do you analyze contracts", "how does this work"]):
            return (
                "Term Shield uses an end-to-end processing pipeline that extracts text from uploaded contract documents, "
                "segments them into clauses, and uses Google Gemini with a grounded retrieval system to provide verified, accurate answers."
            )

        if any(w in q_low for w in ["thank", "thx", "dhanyavadalu", "shukriya", "nandri"]):
            if language == "Telugu":
                return "మీకు స్వాగతం! మీ కాంట్రాక్ట్ గురించి మరిన్ని ప్రశ్నలు ఉంటే తప్పకుండా అడగండి."
            elif language == "Hindi":
                return "आपका स्वागत है! यदि आपके अनुबंध के बारे में कोई अन्य प्रश्न हैं, तो अवश्य पूछें।"
            elif language == "Tamil":
                return "நல்வரவு! உங்கள் ஒப்பந்தம் குறித்து மேலும் கேள்விகள் இருந்தால் கேளுங்கள்."
            return "You're welcome! Feel free to ask if you have any other questions about your contract."

        if any(w in q_low for w in ["okay", "ok", "got it", "understood", "yup", "yeah", "yes"]):
            if language == "Telugu":
                return "సరే! మీ కాంట్రాక్ట్ గురించి మీకు ఇంకా ఏవైనా సందేహాలు ఉంటే అడగండి."
            elif language == "Hindi":
                return "ठीक है! यदि आपके अनुबंध के बारे में कोई और प्रश्न हैं, तो मुझे बताएं।"
            elif language == "Tamil":
                return "சரி! உங்கள் ஒப்பந்தம் குறித்து வேறு ஏதேனும் கேள்விகள் இருந்தால் கேளுங்கள்."
            return "Got it! Feel free to ask if you'd like me to explain anything else in your contract."

        if language == "Telugu":
            return "నమస్కారం! నేను Term Shield AI అసిస్టెంట్‌ని. మీ కాంట్రాక్ట్ నిబంధనలు, చెల్లింపులు, బాధ్యతలు, గడువులు మరియు రిస్క్‌లను విశ్లేషించడంలో నేను మీకు సహాయపడగలను."
        elif language == "Hindi":
            return "नमस्ते! मैं Term Shield AI सहायक हूँ। मैं आपके अनुबंध की शर्तों, भुगतानों, दायित्वों और जोखिमों को समझने में आपकी सहायता कर सकता हूँ।"
        elif language == "Tamil":
            return "வணக்கம்! நான் டெர்ம் ஷீல்ட் AI உதவியாளர். உங்கள் ஒப்பந்த விதிமுறைகள், பொறுப்புகள் மற்றும் அபாயங்களை புரிந்து கொள்ள நான் உதவ முடியும்."
        return "Hello! I am Term Shield's contract assistant. I can help you understand your agreement, explain clauses, highlight obligations, check deadlines, and point out potential risks."

    @classmethod
    def _handle_capability(cls, question: str, language: str) -> str:
        q_low = question.lower()
        from app.core.config import get_settings
        gemini_model = get_settings().gemini_model

        if any(w in q_low for w in ["gemini", "what ai", "what model", "machine learning"]):
            if language == "Telugu":
                return f"అవును, నేను Google Gemini మోడల్ ('{gemini_model}') ద్వారా ఆధారితమైన Term Shield AI అసిస్టెంట్‌ని. మీ కాంట్రాక్ట్‌లను విశ్లేషించడానికి ప్రత్యేకమైన retrieval and grounding system ఉపయోగిస్తాను."
            return (
                f"Yes, I am powered by Google Gemini, configured with the '{gemini_model}' model. "
                "I operate as Term Shield's contract assistant, using a dedicated retrieval and grounding system "
                "to analyze, explain, and review your uploaded documents accurately."
            )

        if any(w in q_low for w in ["what questions should i ask", "what can i ask", "ఏమేమి అడగవచ్చు"]):
            if language == "Telugu":
                return (
                    "మీరు మీ కాంట్రాక్ట్ గురించి అనేక ప్రశ్నలు అడగవచ్చు:\n"
                    "- నా చెల్లింపు బాధ్యతలు ఏమిటి? (What are my payment obligations?)\n"
                    "- నేను ఈ ఒప్పందాన్ని రద్దు చేయవచ్చా? (Can I terminate this contract?)\n"
                    "- నోటీసు వ్యవధి ఎంత? (What is the notice period?)\n"
                    "- నిర్దిష్ట క్లాజ్‌ను సులభంగా వివరించండి.\n"
                    "మీ ప్రశ్నలను సహజంగా అడగండి."
                )
            return (
                "Here are some helpful questions you can ask me about your contract:\n\n"
                "- What are my payment obligations?\n"
                "- Can I terminate this contract?\n"
                "- What is the notice period?\n"
                "- Explain Clause 4 in simple language.\n\n"
                "Ask me naturally — you don't need to use specific keywords."
            )

        if any(w in q_low for w in ["how do you work", "how do you analyze contracts", "how does this work"]):
            return (
                "Term Shield uses an end-to-end processing pipeline that extracts text from uploaded contract documents, "
                "segments them into clauses, and uses Google Gemini with a grounded retrieval system to provide verified, accurate answers."
            )

        if language == "Telugu":
            return (
                "నేను Term Shield AI కాంట్రాక్ట్ అసిస్టెంట్‌ని. మీ ఒప్పందంలోని:\n"
                "- క్లాజ్‌లు మరియు నిబంధనలను సులభంగా వివరించగలను (clauses)\n"
                "- payment obligations (చెల్లింపు బాధ్యతలు) మరియు గడువులను గుర్తించగలను\n"
                "- రద్దు నిబంధనలు మరియు సంభావ్య రిస్క్‌లను విశ్లేషించగలను."
            )
        elif language == "Hindi":
            return (
                "मैं Term Shield AI अनुबंध सहायक हूँ। आपके दस्तावेज़ के आधार पर मैं:\n"
                "- खंडों (clauses) को सरलता से समझा सकता हूँ\n"
                "- payment obligations (भुगतान दायित्व) और समयसीमा बता सकता हूँ\n"
                "- समाप्ति नीतियां और अनुबंध के जोखिम स्पष्ट कर सकता हूँ।"
            )
        return (
            "I am Term Shield AI, your intelligent contract analysis assistant. I can:\n"
            "- Analyze clauses and explain what they mean in simple terms\n"
            "- Identify your payment obligations, fees, and penalties\n"
            "- Review termination terms and notice periods\n"
            "- Highlight key legal risks and responsibilities\n"
            "- Explain contract terms in multiple languages including Telugu and Hindi."
        )

    @classmethod
    def _handle_unrelated(cls, question: str, language: str) -> str:
        if language == "Telugu":
            return (
                "నేను ప్రధానంగా మీ కాంట్రాక్ట్ నిబంధనలను విశ్లేషించడానికి రూపొందించబడ్డాను. "
                "దయచేసి మీ ఒప్పందంలోని నిబంధనలు, బాధ్యతలు లేదా రిస్క్‌ల గురించి అడగండి."
            )
        elif language == "Hindi":
            return (
                "मैं मुख्य रूप से आपके अनुबंध में सहायता के लिए डिज़ाइन किया गया हूँ। "
                "कृपया अपने अनुबंध की शर्तों, भुगतानों या जोखिमों के बारे में प्रश्न पूछें।"
            )
        return (
            "I am designed to assist with contract analysis and legal agreements. "
            "Please ask a question related to your uploaded contract, its clauses, obligations, deadlines, or risks."
        )
