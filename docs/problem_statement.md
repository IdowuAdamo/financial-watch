# FinancialWatch: Problem Statement & Domain Analysis

## 1. Executive Summary
In the Nigerian financial ecosystem, viral misinformation poses an acute operational, systemic, and reputational risk. False insolvency rumours, fabricated Central Bank of Nigeria (CBN) directives, and phishing campaigns can trigger catastrophic deposit flight within hours. **FinancialWatch** is an enterprise-grade RAG-grounded verification pipeline with an agentic retrieval loop, deterministic guardrails, and a human approval gate, engineered specifically to detect, verify, classify, and counter financial misinformation targeting Nigerian commercial banks, grounded strictly in authoritative regulatory knowledge.

---

## 2. The Nigerian Financial Misinformation Threat Landscape

### 2.1 Anatomy of Financial Misinformation
Financial misinformation in Nigeria manifests across four primary vectors:

```
                    ┌──────────────────────────────────────────────┐
                    │ Nigerian Financial Misinformation Vectors    │
                    └──────────────────────┬───────────────────────┘
                                           │
         ┌──────────────────┬──────────────┴─────┬──────────────────┐
         ▼                  ▼                    ▼                  ▼
┌──────────────────┐ ┌───────────────┐ ┌──────────────────┐ ┌───────────────┐
│ Systemic Rumours │ │ Fake Reg Docs │ │ BVN/OTP Scams    │ │ Brand Attacks │
│ Bank insolvency  │ │ Fabricated    │ │ Credential       │ │ Targeted FUD  │
│ & panic runs     │ │ circulars     │ │ harvesting       │ │ on competitors│
└──────────────────┘ └───────────────┘ └──────────────────┘ └───────────────┘
```

1. **Systemic Bank Run Rumours:** Unsubstantiated claims alleging that a commercial bank has lost its operating license or entered liquidation. In an economy sensitive to historical bank failures, such rumours trigger immediate digital withdrawals and physical branch queues.
2. **Fabricated Regulatory Directives:** Fraudulent PDF circulars or forged letterheads bearing the CBN or NDIC emblem, announcing arbitrary deposit freezes, recapitalisation cancellations, or currency restrictions.
3. **BVN & Credential Phishing:** Recurring campaigns claiming that Bank Verification Numbers (BVN) have expired after 10 years, or threatening that accounts will be frozen unless a fee is paid or credentials are provided via unverified WhatsApp numbers.
4. **Targeted Disinformation Campaigns:** Coordinated social media attacks targeting specific institutions during leadership transitions, product updates, or system maintenance windows.

### 2.2 The Nigerian Linguistic Landscape: Pidgin & Code-Mixing
A critical limitation of generic off-the-shelf NLP tools is their inability to process Nigerian Pidgin (Naija) and colloquial code-mixing. Misinformation frequently spreads fastest through vernacular expressions:
- *"Make una go withdraw all una money from [Bank] o! Wahala dey serious, CBN don seize their paper!"*
- *"Una BVN don expire! If you no renew am before Friday with 5k, your account go block kpatakpata!"*
- *"No leave your kudi there o, I hear say management don run."*

Generic models often misinterpret these as sentiment noise or fail to extract the underlying legal and financial claims. FinancialWatch incorporates a dedicated **Pidgin Normalization and Entity Resolution** layer that translates colloquial expressions into normalized search tokens while preserving the original cultural context for response synthesis.

---

## 3. Stakeholder Impact Analysis

| Stakeholder Group | Operational Risk Exposure | FinancialWatch Value Proposition |
| :--- | :--- | :--- |
| **Bank Risk & Compliance Officers** | Undetected rumours escalate into liquidity crunches before official communications can mobilize. | Sub-minute detection, automated grounded verification, and quantified risk scoring (0–100 scale). |
| **Corporate Communications Teams** | Inability to produce authoritative, cited counter-narratives quickly; risk of defensive tone backfiring. | Automated dual-tone response generation (official corporate statement + culturally resonant Pidgin advisory) with verified regulatory citations. |
| **Regulatory Authorities (CBN, NDIC)** | Public panic eroding confidence in the national payment system and banking sector stability. | Direct alignment with official circulars and licensed bank directories, preventing regulatory misattribution. |
| **Retail Depositors & Consumers** | Loss of funds through panic withdrawal costs or falling victim to phishing/credential theft. | Clear debunking of scam typologies and authoritative clarification of regulatory consumer protections. |

---

## 4. The Failure of Ungrounded Generative AI
Deploying vanilla LLMs without grounded retrieval introduces unacceptable risk:
- **Hallucinated Regulatory Policy:** Unconstrained models frequently invent circular reference numbers or confirm fictitious directives based on training artifacts.
- **Unjustified Confidence:** Generic models lack an abstention mechanism; when evidence is absent, they guess rather than declaring `insufficient_evidence`.
- **Absence of Provenance:** Legal and compliance teams cannot publish counter-statements without cryptographic or verifiable URL links to official gazettes.

**FinancialWatch solves this through the Zero-Unanchored-Hallucination Mandate:** no post is classified as `contradicted` or `supported` unless directly substantiated by retrieved passages from authoritative Nigerian regulatory repositories or verified simulated client corporate records.
