"""
Forecast generation script — §10.

Uses a simple but effective approach:
  1. Load sales_history.csv (weekly, up to 2026-09-21)
  2. For each SKU in lead_times.csv, fit a weighted moving average with:
     - Trend adjustment (linear regression over last 26 weeks)
     - Seasonal adjustment (same-week-of-year in prior years)
     - Promotion lift (1.25x multiplier when promo_flag=1 in promo_calendar)
     - Festive lift (Diwali ±1 week → 1.4x multiplier)
  3. Forecast the 4 weeks: 2026-09-28, 2026-10-05, 2026-10-12, 2026-10-19
  4. Write ml/forecast.csv

Run from the project root:
    python ml/generate_forecast.py
"""
import csv
import math
import os
from datetime import date, timedelta
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
if not DATA_DIR.exists():
    DATA_DIR = Path(__file__).resolve().parent.parent.parent / "data"

ML_DIR = Path(__file__).resolve().parent
OUTPUT_FILE = ML_DIR / "forecast.csv"

TRAIN_CUTOFF_DATE = date(2026, 9, 21)  # Strict line preventing any future data leak into training

FORECAST_WEEKS = [
    date(2026, 9, 28),
    date(2026, 10, 5),
    date(2026, 10, 12),
    date(2026, 10, 19),
]
PROMO_LIFT = 1.25
FESTIVAL_LIFT = 1.40
FESTIVAL_WINDOW_WEEKS = 1  # weeks before/after Diwali


def load_csv(path):
    with open(path, encoding="utf-8") as f:
        return list(csv.DictReader(f))


def to_date(s):
    return date.fromisoformat(s.strip())


def week_of_year(d):
    return d.isocalendar()[1]


def main():
    # ── Load data ──────────────────────────────────────────────────────────
    history_rows = load_csv(DATA_DIR / "sales_history.csv")
    lead_rows = load_csv(DATA_DIR / "lead_times.csv")
    promo_rows = load_csv(DATA_DIR / "promo_calendar.csv")
    festival_rows = load_csv(DATA_DIR / "festival_calendar.csv")

    forecast_skus = [r["sku"] for r in lead_rows]

    # ── Promo flags for forecast weeks ────────────────────────────────────
    promo_flags = {}  # (sku, week_start_date) -> 1 or 0
    for r in promo_rows:
        promo_flags[(r["sku"], to_date(r["week_start"]))] = int(r["promo_flag"])

    # ── Festival dates ────────────────────────────────────────────────────
    festival_dates = []
    for r in festival_rows:
        festival_dates.append(to_date(r["date"]))

    def is_festive_week(week_start):
        for fd in festival_dates:
            diff = abs((week_start - fd).days)
            if diff <= FESTIVAL_WINDOW_WEEKS * 7:
                return True
        return False

    # ── Build per-SKU history ─────────────────────────────────────────────
    sku_history = {}  # sku -> list of (date, units_sold, promo_flag)
    for r in history_rows:
        sku = r["sku"]
        d = to_date(r["week_start"])
        if d > TRAIN_CUTOFF_DATE:
            continue  # Line 88: Strict guard stopping future data from leaking into training
        units = float(r["units_sold"])
        promo = int(r.get("promo_flag", 0))
        sku_history.setdefault(sku, []).append((d, units, promo))

    # Sort each SKU's history by date
    for sku in sku_history:
        sku_history[sku].sort(key=lambda x: x[0])

    # ── Forecast each SKU ─────────────────────────────────────────────────
    results = []  # (sku, week_start, forecast_units)

    for sku in forecast_skus:
        hist = sku_history.get(sku, [])

        if not hist:
            # No history — forecast 0
            for w in FORECAST_WEEKS:
                results.append((sku, w.isoformat(), 0.0))
            continue

        # Use up to last 52 weeks for base demand
        recent = hist[-52:]
        units_values = [u for _, u, _ in recent]
        n = len(units_values)

        if n == 0:
            base = 0.0
        else:
            base = sum(units_values) / n

        # Simple trend: linear regression over last 26 weeks
        trend_data = hist[-26:]
        if len(trend_data) >= 4:
            xs = list(range(len(trend_data)))
            ys = [u for _, u, _ in trend_data]
            mean_x = sum(xs) / len(xs)
            mean_y = sum(ys) / len(ys)
            num = sum((x - mean_x) * (y - mean_y) for x, y in zip(xs, ys))
            den = sum((x - mean_x) ** 2 for x in xs)
            slope = num / den if den > 0 else 0.0
        else:
            slope = 0.0

        # Seasonal index: compare same week-of-year to overall mean
        woy_totals = {}
        woy_counts = {}
        for d, u, _ in hist:
            woy = week_of_year(d)
            woy_totals[woy] = woy_totals.get(woy, 0) + u
            woy_counts[woy] = woy_counts.get(woy, 0) + 1

        overall_mean = base if base > 0 else 1.0
        woy_means = {
            woy: woy_totals[woy] / woy_counts[woy]
            for woy in woy_totals
        }

        for i, week_start in enumerate(FORECAST_WEEKS):
            # Weeks into future from last history point
            future_week = len(recent) + i

            # Trend projection
            trended = base + slope * (len(trend_data) + i - len(trend_data) // 2)
            trended = max(0, trended)

            # Seasonal adjustment
            woy = week_of_year(week_start)
            seasonal_mean = woy_means.get(woy)
            if seasonal_mean is not None and overall_mean > 0:
                seasonal_ratio = seasonal_mean / overall_mean
                # Blend: 60% trended, 40% seasonal
                forecast_val = 0.6 * trended + 0.4 * (trended * seasonal_ratio)
            else:
                forecast_val = trended

            # Promo lift
            if promo_flags.get((sku, week_start), 0) == 1:
                forecast_val *= PROMO_LIFT

            # Festive lift (Diwali)
            if is_festive_week(week_start):
                forecast_val *= FESTIVAL_LIFT

            forecast_val = max(0.0, forecast_val)
            results.append((sku, week_start.isoformat(), round(forecast_val, 2)))

    # ── Write output ──────────────────────────────────────────────────────
    ML_DIR.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_FILE, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["sku", "week_start", "forecast_units"])
        for sku, ws, fu in results:
            writer.writerow([sku, ws, fu])

    print(f"Wrote {len(results)} rows to {OUTPUT_FILE}")
    # Verify
    unique_skus = len({r[0] for r in results})
    print(f"SKUs: {unique_skus}, Weeks: {len(FORECAST_WEEKS)}, Total rows: {len(results)}")


if __name__ == "__main__":
    main()
