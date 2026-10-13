# DealerDesk — AI/ML Track

**Provider:** Google Gemini | **Model:** `gemini-1.5-flash`

## What's built

| Section | Status |
|---|---|
| §4 Products (CRUD + search/filter) | ✅ |
| §5 Inventory (PUT to set stock) | ✅ |
| §6 Dealers (list/create/detail) | ✅ |
| §7.1 Orders (create DRAFT, GET, list) | ✅ |
| §7.2–§7.5 Full order engine (confirm, dispatch, deliver, cancel, GST, idempotency, order numbers) | ✅ |
| §8 Supplier sync | ✅ (bonus) |
| §9 Dealer Assistant (Gemini + tool calling) | ✅ |
| §10 Forecasting & reorder | ✅ |

## Setup

```bash
# 1. Copy .env.example to .env and fill in values
cp .env.example .env

# 2. Install dependencies
pip install -r requirements.txt

# 3. Migrate and seed (run twice to verify idempotency)
python manage.py migrate --noinput
python manage.py seed_data
python manage.py seed_data

# 4. Generate forecast (already committed as ml/forecast.csv)
python ml/generate_forecast.py

# 5. Run server
python manage.py runserver 0.0.0.0:8000
```

## Testing

```bash
# Run the complete test suite (31 tests across core, products, orders, forecasting, assistant)
python manage.py test
```

## Smoke test

```bash
python smoke_test.py --base-url http://localhost:8000 --track aiml
python smoke_test.py --base-url http://localhost:8000 --all
```

## Supplier sync (optional)

```bash
# In one terminal
python ../supplier_mock/mock_supplier.py --calm

# In another terminal (with SUPPLIER_API_URL + SUPPLIER_API_KEY set)
curl -X POST http://localhost:8000/api/sync/supplier/
```

## Project layout

```
dealerdesk_project/
├── dealerdesk/          # Django project settings & URL root
├── core/                # Health endpoint + seed_data command
├── products/            # §4 Products, §5 Inventory, §6 Dealers
├── orders/              # §7 Orders (full engine)
├── assistant/           # §9 Gemini-powered dealer assistant
├── forecasting/         # §10 Forecast endpoints + §8 supplier sync
├── ml/
│   ├── forecast.csv     # 160-row forecast (40 SKUs × 4 weeks)
│   └── generate_forecast.py
└── requirements.txt
```

## LLM details

- **Provider:** Google Gemini
- **Model:** `gemini-1.5-flash`
- **Key variable:** `GEMINI_API_KEY`
- **Tool calling:** yes — `search_parts`, `check_stock`, `create_draft_order`
- **Session memory:** persisted per `session_id` in PostgreSQL (`assistant_chat_session` table)

## Video walkthrough

- **Link:** [Project Video Walkthrough](https://1drv.ms/v/c/94e2656cdfcaf110/IQBu8HpeCH4dQrtrzUb25knAASCL6SlAS7NRdDbTaT_sHOc?e=XrZO8V)

## Assumptions

- PostgreSQL database is provisioned and supplied via the `DATABASE_URL` environment variable.
- For local testing without a live PostgreSQL service, `python manage.py test` seamlessly defaults to in-memory SQLite to allow immediate verification of all 31 business rule tests.
- Orders follow the `Asia/Kolkata` timezone for generating date sequences in order numbers (`ORD-YYYYMMDD-NNNN`).
- 18% GST is calculated per line item and rounded with `ROUND_HALF_UP` to 2 decimal places.

