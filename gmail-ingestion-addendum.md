# Addendum: Gmail Ingestion Path for Card Benefit Activation Engine

## 1. Why this addendum exists

The current system's transaction and trigger-event data comes entirely from `/simulator/run-scenario` — pre-baked, reliable, but visibly synthetic to a judge. Card issuers (including Amex) send real-time purchase alert emails with merchant, amount, and date. Sourcing transactions from those emails instead of a fake feed closes that credibility gap and gives the project a "this works on real-world messy input" story.

**This is an addition, not a replacement.** `/simulator/run-scenario` stays exactly as-is — it remains the guaranteed-to-work demo fallback if Gmail auth or parsing hiccups live. The Gmail path becomes a second, parallel way to populate the same pipeline.

## 2. Honest scope — what Gmail can and can't cover

Be precise about this in your project write-up, or you risk overclaiming in front of a judge:

| Benefit type | Gmail-sourced? | Why |
|---|---|---|
| Transaction (the purchase itself) | **Yes** | Issuers reliably send "Instant Alert" / purchase notification emails with merchant, amount, date |
| Travel-delay trigger event | **Yes** | Airlines commonly send delay/cancellation notification emails |
| Theft-report trigger event | **No — stays manual** | Requires a police report number; there is no realistic email source for this |
| Return-denial trigger event | **No — stays manual** | A store manager's verbal/written refusal isn't something that arrives as an email in a real workflow |

So concretely: **Gmail feeds `/transactions/ingest` for all purchases, and additionally feeds `/events/ingest` for flight-delay events.** Theft and return-denial events continue to be entered manually (via your existing simulator or a manual entry form) — this is realistic, not a limitation to hide.

## 3. Architecture — where this plugs into the existing system

```
┌─────────────────┐        ┌──────────────────────┐        ┌───────────────────────┐
│   Test Gmail      │        │   Gmail Poller Module  │        │  Existing FastAPI App   │
│   Inbox            │──IMAP/─▶│   (new, isolated)      │──HTTP─▶│  /transactions/ingest   │
│  (alerts seeded)   │  API   │                        │  POST  │  /events/ingest         │
└─────────────────┘        │  - fetch unread emails │        │  (UNCHANGED)             │
                             │  - classify: purchase   │        └───────────────────────┘
                             │    alert vs flight delay│                    │
                             │  - parse fields          │                    ▼
                             │  - dedupe by email ID    │        Rule matcher + ML layer
                             └──────────────────────┘        (UNCHANGED — no changes needed)
```

**Key principle:** the poller is a new, self-contained module that only ever calls your two existing ingestion endpoints. It does not touch `rules.py`, `ml_layer.py`, `train_ml.py`, or any detection logic. Your rule matcher and ML scorer have no idea whether a transaction came from the simulator or from Gmail — this is exactly why it's safe to add this late without risking what already works.

## 4. Auth setup

Use a **test Gmail account you control**, not a judge's or your personal inbox — this avoids OAuth consent-screen friction during setup and avoids any privacy overreach you don't need for a demo.

1. Create a Google Cloud project (console.cloud.google.com).
2. Enable the **Gmail API** for that project.
3. Create OAuth 2.0 credentials (Desktop app type is simplest for a local script — avoids needing a public redirect URI).
4. Set the scope to `https://www.googleapis.com/auth/gmail.readonly` — read-only is all you need, and it's an easy point to mention in your write-up as a deliberate least-privilege choice.
5. Run the standard `google-auth-oauthlib` installed-app flow once locally to generate a `token.json`; the poller reuses this token on subsequent runs (refreshes automatically via the library).
6. Seed the test inbox with realistic alert emails before the demo — either forward real alert-style emails to it, or send yourself emails matching the templates in section 5. Do this well before demo day, not live.

Dependencies to add to `backend/requirements.txt`:
```
google-auth
google-auth-oauthlib
google-api-python-client
```

## 5. Email parsing approach

### 5.1 Classify first, then extract
When the poller fetches unread messages, first classify each as one of: `purchase_alert`, `flight_delay_alert`, or `irrelevant` (skip). Use sender domain + subject keywords for this — cheap and reliable:
- `purchase_alert`: sender contains issuer domain (e.g., `americanexpress.com`) and subject contains "purchase" / "transaction" / "alert"
- `flight_delay_alert`: sender is an airline domain and subject contains "delay" / "cancelled" / "schedule change"
- everything else: skip

### 5.2 Field extraction — regex first, LLM fallback second
Real alert emails follow a fairly consistent template per issuer, so start with regex against the email body (plain text, not HTML — request `text/plain` MIME part first, fall back to stripped HTML):

**Purchase alert — typical fields to extract:**
- Merchant name (usually after "at" or "made at")
- Amount (`$\d+\.\d{2}` pattern)
- Card product / last 4 digits (maps to `card_member_id` via a lookup table you maintain, since email doesn't carry your internal member ID)
- Date/time of transaction

**Flight delay alert — typical fields to extract:**
- Airline name (from sender domain or signature)
- Flight number (pattern like `[A-Z]{2}\d{2,4}`)
- Delay duration in hours (parse phrases like "delayed by X hours" or compute from old vs. new departure time if both are present)

**Fallback for messy/unstructured bodies:** if regex extraction fails to find required fields with reasonable confidence, send the email body text to an LLM API call with a strict prompt: *"Extract merchant name, amount, and date from this purchase alert email. Respond only as JSON: {merchant, amount, date}. If a field is not present, use null."* This is your second differentiator to mention in the write-up — "handles messy real-world input, not just one clean template" — but keep it as a fallback, not the primary path, so parsing doesn't depend on an external API call being available during the live demo.

### 5.3 Deduplication
Store the Gmail message ID alongside each ingested transaction (a new `source_email_id` column, nullable, on the `Transaction` model — additive, doesn't touch existing rows). Before ingesting, check if that message ID has already been processed; skip if so. This makes the poller safely re-runnable without creating duplicate transactions.

## 6. Poller implementation shape

New file: `backend/gmail_poller.py` — kept fully separate from `rules.py` / `ml_layer.py` / `main.py`'s detection logic.

```python
# backend/gmail_poller.py  (shape, not full implementation)

def fetch_unread_alert_emails() -> list[dict]:
    """Authenticates via stored token, queries Gmail for unread messages
    matching known issuer/airline sender domains, returns raw email data."""
    ...

def classify_email(email: dict) -> str:
    """Returns 'purchase_alert' | 'flight_delay_alert' | 'irrelevant'."""
    ...

def extract_purchase_fields(body: str) -> dict | None:
    """Regex extraction; returns None if required fields not found."""
    ...

def extract_flight_delay_fields(body: str) -> dict | None:
    ...

def llm_fallback_extract(body: str, expected_type: str) -> dict | None:
    """Used only when regex extraction fails."""
    ...

def run_poll_cycle(api_base_url: str = "http://localhost:8000"):
    """Main entrypoint: fetch → classify → extract → dedupe → POST to
    /transactions/ingest or /events/ingest on the existing FastAPI app.
    Marks processed emails as read (or labels them) so they aren't reprocessed."""
    ...
```

Expose it two ways, both additive:
- **On-demand:** a new endpoint `POST /gmail/poll-now` on the existing FastAPI app that just calls `run_poll_cycle()` synchronously — lets you trigger it live during the demo with a button click.
- **Scheduled (optional, nice-to-have):** a simple `asyncio` background task started at app startup that calls `run_poll_cycle()` every N seconds, so new alert emails get picked up automatically without a manual trigger. Only add this if the on-demand version is solid first — a flaky background poller is worse than none.

## 7. Frontend addition (small, additive)

Add a "Sync from Gmail" button to `SimulatorControls.tsx` alongside the existing scenario buttons, calling `POST /gmail/poll-now`. Show a simple result toast: "Found 2 new transactions, 1 flight delay — 1 claim auto-detected." This sits next to, not instead of, the existing simulator buttons.

## 8. Demo script update

Revise the existing demo flow to lead with the Gmail path and keep the simulator as the visible fallback:

1. Open the seeded test Gmail inbox briefly — show a real-looking purchase alert email sitting there.
2. Click "Sync from Gmail" in the app.
3. Show the new transaction appear, get evaluated, and (if a linked flight-delay email was also present) show the claim auto-detect with full reasoning — same "Why am I seeing this?" panel as before, unchanged.
4. Narrate explicitly: *"Purchases and flight delays come in through real email alerts. Theft reports and return denials still require documentation like a police report or a store's written refusal, so those stay as manual entry — which mirrors how these claims actually work today."* This preempts the "why isn't everything automated" question before a judge asks it.
5. If Gmail sync fails live for any reason (network, auth token expiry), fall back immediately to `/simulator/run-scenario` — same claims, same reasoning engine, no visible difference in the rest of the demo.

## 9. What does NOT change

Confirm explicitly in your write-up that this addition touches zero detection logic:
- `rules.py` — unchanged
- `ml_layer.py` / `train_ml.py` — unchanged
- `policies.json` — unchanged
- Claim state machine (`main.py` status transitions, entitlement caps) — unchanged
- Frontend `ClaimFeed.tsx` / `ClaimDetail.tsx` / `AdminDashboard.tsx` reasoning display — unchanged

The only new surface area is: one new module (`gmail_poller.py`), one new endpoint (`/gmail/poll-now`), one new nullable DB column (`source_email_id`), and one new frontend button. This is the honest scope to describe if asked how much of the existing, already-tested system you had to touch.
