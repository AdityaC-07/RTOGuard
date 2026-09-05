# RTOGuard — Pre-Checkout RTO Fraud Scorer for Indian E-commerce

<div align="center">

![Python](https://skillicons.dev/icons?i=py,fastapi,react,ts,tailwind,sqlite,sklearn&theme=light)

![XGBoost](https://img.shields.io/badge/XGBoost-3.x-EB5B27?logo=xgboost&logoColor=white)
![pandas](https://img.shields.io/badge/pandas-3.x-150458?logo=pandas&logoColor=white)
![NumPy](https://img.shields.io/badge/NumPy-2.x-013243?logo=numpy&logoColor=white)
![pytest](https://img.shields.io/badge/pytest-15_passing-0A9EDC?logo=pytest&logoColor=white)
![License](https://img.shields.io/badge/license-MIT-blue)

**Score the risk of a Cash-on-Delivery return *before* the order ships — in rupees, not probabilities.**

</div>

---

## The problem

COD returns (RTO) cost Indian merchants **~₹1,200 per order** in forward + reverse logistics, while wrongly blocking a genuine customer costs only **~₹400** in friction. Off-the-shelf fraud models optimise accuracy and treat both errors equally — so they systematically under-block fraud. RTOGuard optimises **money directly**: every threshold, model choice, and evaluation metric is denominated in INR.

## How it works

```
Checkout form ──POST /v1/score/rto──▶ FastAPI ──▶ DecisionEngine
                                                      │
                         ┌────────────────────────────┼────────────────────────────┐
                         │ Verified buyer?            │ Model path                 │ Fallback
                         │ last-10-digit match        │ 47-feature vector          │ rule-based,
                         │ → APPROVE, score 5         │ → stacked ensemble         │ never 500
                         └────────────────────────────┴────────────────────────────┘
                                                      │ writes every order to SQLite
                                                      ▼ verdict card: score dial + reasons + breakdown
```

1. **Featurise (47 signals).** Address quality (6) + fraud-ring graph proxies (5) + behavioural history over a 90-day SQLite store (11) + Indian address parser (8) + phone-shape analysis (5) + IP intelligence (7) + order-time signals (5).
2. **Score.** A 3-branch stacked ensemble (address / identity / network `XGBClassifier`s + logistic meta-learner) trained with a **custom asymmetric XGBoost objective** where missed fraud carries a 3× gradient penalty (₹1200/₹400).
3. **Decide in rupees.** The decision threshold is swept 0.25–0.75 to maximise **Net Financial Saved Value**: `NFSV = TP×1200 − FP×400 − FN×1200`. Tiers: `APPROVE` / `REQUIRE_PREPAID` / `FLAG_FOR_REVIEW`.
4. **Learn.** Every scored order persists to SQLite; confirmed RTOs (`POST /v1/confirm-rto`) become ground-truth labels that shift future scores for the whole device ring.

## Tech stack

| Layer | Technology |
|---|---|
| API | FastAPI + Pydantic v2, CORS for the dashboard, zero-500 guarantee (every handler degrades) |
| ML | XGBoost 3.x (custom dual-API objective), scikit-learn (ensemble meta-learner, leakage probes), pandas/NumPy |
| Storage | SQLite (stdlib only) — order history, device/address clusters, dispute + confirmation records |
| Frontend | React 18 + TypeScript, Tailwind, Recharts, Zustand, Axios, Framer Motion |
| Eval | Synthetic generators (v1 heuristics + v2 adversarial archetypes), NFSV engine, per-archetype reports |
| Tests | pytest (15 tests: features, scorer, API, Phase-2 history) |

## Project structure

```
.
├── app/
│   ├── api/            # routes.py (/health, /v1/score/rto), extended.py (spike/rings/disputes/threshold),
│   │                   # confirm.py (ground truth), verification.py (OTP stubs — SMS deferred)
│   ├── core/           # guardrails.py — verified override, tiering, history bump, fallbacks
│   ├── db/             # SQLite store + history-signal queries (canonicalisation, bursts, trajectories)
│   ├── features/       # address, ring_signals, history_signals, address_intelligence,
│   │                   # phone_signals, ip_signals, time_signals, pipeline (47-dim)
│   └── models/         # custom_obj (asymmetric loss), scorer (CSL-OCRL), ensemble, trainer
├── eval/               # generate_data (v1), generate_data_v2 (8 fraud + 3 legit archetypes),
│                       # metrics (NFSV), train_and_save, evaluate_v2
├── rtoguard-dashboard/ # Merchant dashboard: risk scorer + dial, spike/ring/dispute tabs
├── tests/              # pytest suite
└── requirements.txt
```

## Quickstart

**Backend** (Windows PowerShell; Linux/macOS equivalent):

```powershell
Set-Location C:\Projects\RTOGuard
python -m venv venv; .\venv\Scripts\Activate.ps1
pip install -r requirements.txt
$env:PYTHONPATH = "C:\Projects\RTOGuard"   # required: absolute `from app/eval` imports
chcp 65001                                  # required on Windows for ₹ output
python -m uvicorn app.api.routes:app --reload --port 8000
```

**Train the model** (optional — API falls back to rules without it):

```powershell
python -m eval.train_and_save   # trains ensemble on 5k V2 rows → data/model.pkl
python -m eval.evaluate_v2      # merchant-readable accuracy + per-archetype report
```

Restart uvicorn after training — look for `[RTOGuard] Loaded model from data/model.pkl`.

**Frontend:**

```powershell
Set-Location rtoguard-dashboard
npm install --legacy-peer-deps   # react-scripts@5 vs TS5 peer conflict; skip if node_modules exists
npm run dev                      # http://localhost:3000 (backend must be on :8000)
```

**Tests:** `python -m pytest tests/ -q` (use `python -m pytest`; the bare `pytest.exe` shim is broken under Python 3.14).

## API reference

| Method & path | Purpose |
|---|---|
| `GET /health` | Liveness probe for the dashboard badge |
| `POST /v1/score/rto` | Score one order → `{risk_score, decision, top_risk_factors, estimated_financial_risk_inr, …}` |
| `POST /v1/confirm-rto` | Mark an order confirmed-RTO (ground truth for retraining) |
| `GET /v1/threshold-sweep` | NFSV across decision thresholds |
| `GET /v1/spike/active-cluster`, `GET /v1/spike/metrics/{pin}` | Pincode velocity spikes + traffic decomposition |
| `GET /v1/rings/active`, `GET /v1/rings/{id}`, `POST /v1/rings/{id}/block` | Device-sharing fraud rings mined from order history |
| `GET /v1/disputes/cases`, `GET /v1/disputes/cases/{id}`, `POST …/submit` | Chargeback evidence workflow |
| `POST /v1/verify/send-otp`, `POST /v1/verify/confirm-otp` | Dev-only OTP stubs (SMS gateway deferred) |

## Honest evaluation

We publish the numbers we actually measured, including the bad ones:

- Leakage probes on V2 data: device-alone F1 **0.07**, phone-alone **0.00** (an earlier build scored 1.0 by memorizing device IDs — rebuilt, not hidden).
- Ensemble after de-leaking: val F1 **0.65**, held-out F1 **0.52** (recall 0.80, precision 0.39). Below the 0.82 target — the gap is threshold calibration and confirmed-label volume, tracked openly in the roadmap.
- No silent failures: transformers return neutral defaults on bad input; endpoints never 500; history layer is provably neutral on day 1 (all-zero on empty DB).

## Roadmap

- SMS OTP via Twilio/MSG91 (endpoints stubbed, UI parked behind a TODO)
- Retraining on confirmed labels (500-label trigger designed, unwired)
- Cross-merchant consortium signals (privacy-preserving hash sharing)
- Recall-per-archetype reporting (F1 is undefined on single-class archetype slices)

## License

MIT — free for merchants, hackers, and judges.
