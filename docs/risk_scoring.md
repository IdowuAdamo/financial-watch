# FinancialWatch: Quantified Risk Scoring & Priority Triaging Engine

## 1. Mathematical Formulation

FinancialWatch quantifies the operational and systemic risk posed by incoming narratives using a deterministic 0–100 heuristic scoring model. The overall risk score synthesizes three core dimensions:

$$\text{Overall Risk} = \min\left(100, \text{round}\left(S \cdot w_s + V \cdot w_v + C \cdot w_c\right)\right)$$

Where:
- $S \in [0, 100]$: **Severity Score** (potential systemic/financial damage)
- $V \in [0, 100]$: **Virality Score** (engagement, velocity, and reach)
- $C \in [0, 100]$: **Channel Credibility & Spread Risk** (platform multiplier)
- $w_s = 0.40, w_v = 0.35, w_c = 0.25$: Baseline dimension weights.

---

## 2. Dimension Breakdown & Calculations

### 2.1 Severity Dimension ($S$)
Severity evaluates the inherent danger of the narrative if accepted by the public. It is defined as:

$$S = \text{Base Severity}(\text{Category}) \times \text{Verdict Multiplier}$$

#### Base Category Severity
| Category | Base Score | Operational Justification |
| :--- | :---: | :--- |
| `solvency_distress` | 95 | Insolvency / license revocation rumours directly trigger deposit runs and interbank liquidity crises. |
| `regulatory_enforcement` | 80 | Fabricated regulatory sanctions or recapitalisation cancellations damage investor confidence. |
| `scam_phishing` | 75 | Direct consumer asset loss through BVN credential theft or OTP interception. |
| `fake_advisory` | 65 | Misleading operational directives (e.g. false branch closure notices or fee changes). |
| `operational_outage` | 50 | Claims of total core banking infrastructure failure. |
| `general_sentiment` | 20 | Customer dissatisfaction, service complaints, or generic commentary. |

#### Verdict Multiplier
The verdict determined by the Grounded Verifier scales the severity:
- **`contradicted` ($1.0\times$):** Confirmed false narrative with active misinformation payload. Retains full severity.
- **`scam_alert` ($0.9\times$):** Verified fraud/phishing typology targeting consumer funds.
- **`unverified` ($0.7\times$):** Narrative cannot be confirmed or refuted. Treated with caution as an emerging threat.
- **`supported` ($0.15\times$):** Factual, verified information. Drastically reduced to prevent false alerts on legitimate news.

---

### 2.2 Virality Dimension ($V$)
Virality measures public exposure and velocity, combining engagement metrics and temporal recency:

$$V = \min\left(100, \text{round}\left(\log_{10}(\text{shares} \cdot 2.5 + \text{likes} + 1) \cdot 18 \times \text{Recency Factor}\right)\right)$$

- **Weighting:** Shares are weighted $2.5\times$ higher than likes, reflecting active broadcast intent.
- **Recency Decay:**
  - $< 2$ hours: $1.2\times$ (active outbreak surge)
  - $2 - 6$ hours: $1.0\times$ (peak propagation)
  - $6 - 24$ hours: $0.8\times$ (maturing narrative)
  - $> 24$ hours: $0.5\times$ (historical/residual reach)

---

### 2.3 Channel Multiplier ($C$)
Different communication platforms present distinct contagion dynamics in the Nigerian ecosystem:
- **WhatsApp Broadcast / Groups ($C = 95$):** Highest contagion risk in Nigeria; end-to-end encrypted, high perceived trust, difficult to trace.
- **X (Twitter) ($C = 85$):** Rapid public virality, algorithmic amplification, journalist monitoring.
- **TikTok / Instagram ($C = 80$):** High video virality among youth demographics; rapid visual spread.
- **Facebook ($C = 75$):** Broad demographic reach, high group cross-sharing.
- **LinkedIn / Web Forums ($C = 50$):** Professional context, slower dissemination rate.
- **Paste Intake / Unknown ($C = 60$):** Neutral baseline for unannotated analyst input.

---

## 3. Dynamic Weight Renormalisation for Missing Metadata

In real-world operations, analysts frequently paste raw snippets from text messages or unverified channels without engagement counts (likes/shares) or timestamps. 

A naive scoring system that assumes zero for missing fields would artificially deflate an urgent bank run rumour to a "LOW" risk score. **FinancialWatch resolves this via Dynamic Weight Renormalisation.**

### Renormalisation Rules
When one or more dimensions are missing, their weights are set to 0, and the remaining weights are scaled proportionally to sum to 1.0:

$$w'_i = \frac{w_i}{\sum_{j \in \text{Available}} w_j}$$

### Scenario Comparison

```
Scenario A: Full Metadata Available
  • Inputs: Likes=1,240, Shares=890, Platform=WhatsApp, Text=Apex Horizon Revocation
  • S = 95, V = 72, C = 95
  • Risk = (95 * 0.40) + (72 * 0.35) + (95 * 0.25) = 38.0 + 25.2 + 23.75 = 87 (CRITICAL)

Scenario B: Raw Text Paste (No Likes, No Shares, No Platform)
  • Inputs: Pure text paste only
  • V unavailable (w_v = 0), C unavailable (w_c = 0)
  • Renormalised: w'_s = 1.0
  • Risk = 95 * 1.0 = 95 (CRITICAL)
  • Result: The system does NOT under-triage dangerous rumours due to missing telemetry.
```

---

## 4. Operational Risk Tiers & SLA Escalation

```
┌────────────────────────────────────────────────────────────────────────┐
│ RISK TIERS & INCIDENT ESCALATION MATRIX                                │
├──────────┬──────────┬───────────────────────┬──────────────────────────┤
│ Tier     │ Score    │ Typical Claim         │ Action Protocol          │
├──────────┼──────────┼───────────────────────┼──────────────────────────┤
│ CRITICAL │ 80 - 100 │ False Insolvency,     │ Immediate notification;  │
│          │          │ License Revocation    │ 15-minute response SLA;  │
│          │          │                       │ Executive mobilization.  │
├──────────┼──────────┼───────────────────────┼──────────────────────────┤
│ HIGH     │ 60 - 79  │ Fake Reg Circulars,   │ Queue priority staging;  │
│          │          │ Systemic Cyber Scam   │ 1-hour response SLA.     │
├──────────┼──────────┼───────────────────────┼──────────────────────────┤
│ MEDIUM   │ 40 - 59  │ Local Branch Outage,  │ Standard operator queue; │
│          │          │ Fee Dispute Rumour    │ 4-hour review window.    │
├──────────┼──────────┼───────────────────────┼──────────────────────────┤
│ LOW      │ 0 - 39   │ General Sentiment,    │ Auto-archived;           │
│          │          │ Verified Factual News │ Periodic trend reports.  │
└──────────┴──────────┴───────────────────────┴──────────────────────────┘
```
