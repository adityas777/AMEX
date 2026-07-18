# Card Benefit Activation Engine — Build Specification

## 1. Problem Statement (as given)

Most card members are unaware of or forget to claim the insurance and protection benefits built into their cards. Build a system that automatically detects when a purchase qualifies for coverage — purchase protection, return protection, or travel-delay insurance — and pre-fills the claim so card members never miss a benefit they've already paid for. This is distinct from loyalty/rewards programs — focus entirely on unused insurance and protection benefits.

**Judged on:** detection accuracy, claim pre-fill quality, reduction in unclaimed benefits, clarity of the customer-facing experience, and quality/transparency of the underlying reasoning.

## 2. What We're Building (MVP scope for the hackathon)

A working, demoable pipeline:

1. A stream of simulated card transactions comes in.
2. A **detection engine** (rules + a lightweight ML layer) evaluates each transaction against a set of card benefit policies and decides: (a) does this purchase qualify for coverage, (b) which benefit type, (c) confidence.
3. Qualifying transactions get matched to the correct benefit (Purchase Protection / Return Protection / Travel-Delay Insurance) with entitlement checks (coverage caps, time windows, exclusions).
4. A **pre-filled claim** is generated automatically (claim form fields populated from transaction + policy data).
5. A **customer-facing web app** shows a card member their detected benefits ("You may be covered for this") and lets them review/submit the pre-filled claim in one click.
6. A lightweight **backend/admin view** shows entitlement tracking and claim status (submitted → under review → approved), simulating the approval workflow.
7. A **transparency layer**: every detection/match decision shows *why* (which rule/policy fired, what data supported it) — this is a strong differentiator for judges.

Do NOT build: real payment processing, real insurance underwriting, loyalty/rewards features, real bank integrations. Everything financial is simulated/mocked but should look and behave like production data.

## 3. Recommended Tech Stack

Chosen to match your existing skill set (FastAPI, React, scikit-learn, Docker) rather than the example stack in the PS — the PS says "open to all."

- **Frontend:** React + Vite + TypeScript, Tailwind CSS
- **Backend/API:** Python FastAPI (you've shipped 3+ FastAPI projects already — GHG platform, power forecasting, this fits your fastest path to a working demo)
- **Transaction ingestion / streaming simulation:** Since real Kafka/Pub/Sub setup burns hackathon time, simulate an event stream in-process: a Python generator/async task that "publishes" synthetic transactions on an interval, consumed by the detection engine via an internal queue (`asyncio.Queue` or a simple SQLite-backed outbox). If you want to show you understand the referenced architecture (AWS Lambda, Pub/Sub) without integrating it live, document it in the architecture diagram as the "production path" and note what you built as a local-equivalent simulation for the demo — judges care that you understand the pattern, not that you provisioned real cloud infra during a hackathon.
- **Rules engine:** hand-rolled Python rules module (declarative policy definitions in JSON/YAML, evaluated by a rule matcher) — this doubles as your "transparent reasoning layer."
- **ML layer (optional but recommended for differentiation):** scikit-learn classifier to score "does this transaction look like a qualifying purchase" (e.g., merchant category code + amount + product keywords → benefit-type probability), trained on synthetic labeled transaction data you generate. This shows real ML, not just if/else, addressing feedback you've gotten before about hardcoded logic dressed up as ML.
- **Database:** SQLite for the hackathon (swap-in path to PostgreSQL documented, not required to implement)
- **Containerization:** Docker Compose for frontend + backend + db (you already do this reflexively — keep it)

## 4. Data Model

### 4.1 Card & Cardholder
- `card_member_id`, `name`, `card_product` (e.g., "Platinum Travel", "Everyday Cashback")
- `card_product` determines which benefits apply (not all cards carry all three benefit types)

### 4.2 Benefit Policy (the "rules" — seed this as structured config, not hardcoded in Python)
For each benefit type, define as data (JSON/YAML), not code:
- `benefit_type`: purchase_protection | return_protection | travel_delay
- `eligible_card_products`: []
- `coverage_window_days`: e.g., 90 days from purchase for purchase protection
- `max_coverage_amount`: per-claim and/or annual cap
- `eligible_categories` / `excluded_categories` (merchant category codes — MCCs)
- `trigger_conditions`: what event indicates a claim is warranted (e.g., damaged/stolen item within window; merchant refusal to accept return within their stated policy; flight delay > N hours)
- `required_evidence`: list of fields/documents needed for a valid claim

### 4.3 Transaction
- `transaction_id`, `card_member_id`, `merchant_name`, `mcc` (merchant category code), `amount`, `currency`, `timestamp`, `product_description` (free text — useful for your NLP/keyword matching), `transaction_type` (purchase/return)

### 4.4 Trigger Event (what makes something claimable)
Since real world signals like "item was stolen" or "flight delayed" aren't in a transaction record alone, simulate a secondary event feed for the demo:
- `event_type`: theft_report | damage_report | return_denied | flight_delay
- `related_transaction_id`
- `event_data` (e.g., delay_hours, denial_reason)
- `event_timestamp`

This is realistic — in production these signals would come from customer-service tickets, travel APIs (flight status), retailer webhooks etc. For the hackathon, generate a synthetic event feed that pairs with a subset of transactions.

### 4.5 Detected Benefit / Claim
- `claim_id`, `transaction_id`, `benefit_type`, `confidence_score`, `matched_policy_id`
- `reasoning`: structured explanation (which rules fired, what ML score contributed, which policy clause applies) — render this in the UI, it's your transparency layer
- `pre_filled_fields`: JSON of claim form fields auto-populated
- `status`: detected → pending_review → submitted → approved → paid | denied

## 5. Core Algorithm (Detection & Matching)

Pipeline per incoming transaction (and any linked event):

1. **Eligibility filter** — is the card product covered at all for any benefit? (fast reject)
2. **Rule matcher** — evaluate each benefit policy's `trigger_conditions` against the transaction + any linked event. This is deterministic and explainable — start here, get this rock-solid first, it's your MVP core.
3. **ML confidence scorer** — for ambiguous cases (e.g., product_description doesn't clearly indicate an electronics purchase but MCC suggests it might), use a scikit-learn model (start with logistic regression or a random forest — you have XGBoost experience too) trained on labeled synthetic examples to output a confidence score per benefit type. Combine with rule match: rules give a hard yes/no on eligibility, ML refines confidence/priority when multiple benefits might apply or evidence is partial.
4. **Benefit-type resolution** — if multiple benefit types could apply, pick highest-confidence match; log alternatives considered (for the transparency layer).
5. **Entitlement check** — verify against caps (per-claim max, annual aggregate used so far for that card member) before finalizing.
6. **Claim pre-fill** — populate claim form fields from transaction + policy + event data.
7. **Emit claim record** with status `detected`, ready for card member review.

## 6. API Endpoints (FastAPI)

- `POST /transactions/ingest` — simulate incoming transaction (also drives the demo)
- `POST /events/ingest` — simulate a linked event (theft/damage/return-denied/flight-delay report)
- `GET /card-members/{id}/detected-benefits` — list of detected, unclaimed benefits for a card member
- `GET /claims/{claim_id}` — full claim detail including reasoning/explanation
- `POST /claims/{claim_id}/submit` — card member confirms/edits pre-filled claim and submits
- `PATCH /claims/{claim_id}/status` — admin/ops endpoint to move claim through approval workflow (simulated)
- `GET /card-members/{id}/entitlement-summary` — remaining coverage caps by benefit type
- `GET /admin/claims` — ops dashboard list view with filters by status/benefit type

## 7. Frontend (React)

### Card member view
- **Benefit feed**: card-style list of detected benefits ("Your Sony headphones purchase on July 3 may be covered under Purchase Protection — up to $500"), each with a confidence indicator and a "Why am I seeing this?" expandable explanation (pulls from `reasoning`)
- **Claim review/submit screen**: pre-filled form, editable, clear list of what evidence is still needed, one-click submit
- **Claim status tracker**: simple stepper (Detected → Submitted → Under Review → Approved/Paid)
- **Entitlement summary**: "You have $1,200 of $2,000 annual purchase protection remaining"

### Admin/ops view (simpler, functional over polished)
- Table of all claims with status, benefit type, confidence score, filters
- Click into a claim to see the full reasoning trace (this is a good screen to show judges — it demonstrates the "transparent reasoning layer" task explicitly called out in the PS)

## 8. Demo Script (for the video/live demo)

1. Show a card member with zero awareness of their benefits — a clean starting dashboard.
2. Trigger a simulated transaction ingest (e.g., a $450 electronics purchase) live, then trigger a linked "theft_report" event.
3. Within seconds, the detected-benefit feed updates — show the notification/feed entry appearing.
4. Open "Why am I seeing this?" — walk through the rule that fired + ML confidence score, in plain language.
5. Open the claim — show it's already 90% filled in from transaction + policy data.
6. Submit → show it move through the status tracker.
7. Cut to the admin view — show the reasoning trace for auditability, and the entitlement caps preventing over-claiming.
8. Close with the underutilization angle: "X% of eligible claims go unfiled today — this recovers that value automatically."

## 9. Build Order (prioritize for a time-boxed hackathon)

1. Data models + seed data (card products, benefit policies as config, synthetic transactions, synthetic events) — get realistic-looking data first, it makes everything downstream easier to demo
2. Rule matcher (deterministic detection) — this alone is a working MVP
3. Claim pre-fill logic + claim data model
4. FastAPI endpoints wrapping the above
5. React card-member view (benefit feed → claim review → submit)
6. Reasoning/explanation surfacing in the UI
7. ML confidence scorer layered on top of rules (do this once the rules path works end-to-end — it's a differentiator, not the critical path)
8. Admin/ops view
9. Entitlement cap enforcement
10. Polish, seed a good demo dataset, record video

## 10. Referenced Production Architecture (for the write-up, not required to implement live)

Mention this in your project description/presentation to show you understand how it would run at scale, even though the hackathon build simulates it locally:

- **Transaction ingestion at scale:** Google Pub/Sub (or Kafka) topic per transaction stream; the detection engine subscribes and processes events asynchronously — see [Pub/Sub docs](https://docs.cloud.google.com/pubsub/docs)
- **Serverless detection/matching functions:** AWS Lambda functions triggered per transaction event for the rule-matching and ML-scoring steps, so detection scales independently of the main API — see [AWS Lambda docs](https://docs.aws.amazon.com/lambda/)
- **Real transaction/card data source:** in production this would come from the issuing platform itself (e.g., Stripe Issuing API for card transaction data) rather than a synthetic feed
- Note in your doc: "For the hackathon we simulate the event stream locally to keep the demo self-contained and reliable; the detection/matching logic is architected so the rule matcher and ML scorer could run as independent Pub/Sub-triggered Lambda functions in production without changes to their interfaces."

## 11. Where You're Strong vs. Where to Be Careful

**Strong (lean into these in the presentation):**
- Real ML model with actual training data, not hardcoded confidence scores — you've been dinged before for this exact pattern (e.g., a past project's "Q-learning" turning out to be if/else, confidence hardcoded at 0.87). Make sure the confidence score here is genuinely computed by a trained model on held-out data, and be ready to explain the train/test split if asked.
- The transparency/reasoning layer — this is explicitly called out as a task in the PS and plays to your FastAPI + clean API design habits.
- Docker packaging — you do this well already, keep it consistent.

**Be careful of:**
- Data leakage in the ML confidence scorer (flagged as a gap in past projects) — make sure synthetic training/test transactions don't share identical merchant+amount+description combos across splits.
- Don't let the entitlement/approval workflow become vaporware — a simple but *functioning* status state machine beats an elaborate one that's only half-wired.
- Keep the "production architecture" (Pub/Sub, Lambda) as an honestly-labeled diagram/description, not something you claim to have deployed if you didn't — judges notice overclaiming faster than underclaiming.
