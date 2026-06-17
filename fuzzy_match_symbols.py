"""
Fuzzy Match IPO Stocks → Kite Trading Symbols
===============================================
Matches scraped IPO stock names from screener.in against the Kite
instruments file using fuzzy search, and outputs the best matching
trading symbol for each stock.

Saves results to: ipo_with_symbols.csv
"""

import json
import csv
from thefuzz import fuzz, process


# ── File paths ──────────────────────────────────────────────────────
IPO_CSV = "ipo_mcap_above_500.csv"
KITE_JSON = "kite_instruments.json"
OUTPUT_CSV = "ipo_with_symbols.csv"

# Minimum fuzzy score to consider a match valid (0-100)
MIN_SCORE = 55

# ── Manual overrides for known incorrect fuzzy matches ──────────────
# Format: "IPO Stock Name" → ("SYMBOL", "EXCHANGE")
MANUAL_OVERRIDES = {
    "A C J K Exports":       ("AMIRCHAND",    "NSE"),
    "Emcure Pharma":         ("EMCURE",       "NSE"),
    "Entero Healthcar":      ("ENTERO",       "NSE"),
    "Medi Assist Ser.":      ("MEDIASSIST",   "NSE"),
    "JSW Infrast":           ("JSWINFRA",     "NSE"),
    "Yatharth Hospit.":      ("YATHARTH",     "NSE"),
    "HMA Agro Inds.":        ("HMAAGRO",      "NSE"),
    "IKIO Tech":             ("IKIO",         "NSE"),
    "Garuda Cons":           ("GARUDA",       "NSE"),
    "Indus Inf. Trust":      ("INDUSINVIT",   "NSE"),
    "Jyoti CNC Auto.":       ("JYOTICNC",     "NSE"),
    "KRN Heat Exchan":       ("KRN",          "NSE"),
    "Shree TirupatiBa":      ("TIRUPATI-SM",  "NSE"),
    "Highway Infra":         ("HIGHWAY",      "NSE"),
    "N S D L":               ("NSDL",         "NSE"),
    "Rosmerta Digital":      ("ROSMERTA",     "NSE"),
    "Cyient DLM":            ("CYIENTDLM",    "NSE"),
    "Blue Jet Health":       ("BLUEJET",      "NSE"),
    "Anand Rathi Shar":      ("ABORL",        "NSE"),
    "Interarch Build.":      ("INTERARCH",    "NSE"),
}


def load_kite_instruments(path: str) -> dict:
    """Load Kite instruments and return {full_name: {symbol, exchange, ...}}."""
    with open(path, "r", encoding="utf-8") as f:
        raw = json.load(f)
    return raw["data"]


def load_ipo_stocks(path: str) -> list[dict]:
    """Load scraped IPO stocks from CSV."""
    stocks = []
    with open(path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            stocks.append(row)
    return stocks


def normalize(name: str) -> str:
    """
    Normalize a stock name for better fuzzy matching.
    Expands common abbreviations and removes noise.
    """
    import re
    s = name.strip().upper()

    # Expand common screener abbreviations
    abbreviations = {
        "TECH.": "TECHNOLOGIES",
        "TECHNOL.": "TECHNOLOGIES",
        "ENGG.": "ENGINEERING",
        "PHARMA.": "PHARMACEUTICALS",
        "INFRA.": "INFRASTRUCTURE",
        "INDUSTR": "INDUSTRIES",
        "FINAN": "FINANCE",
        "FINANC.": "FINANCE",
        "HOSPIT.": "HOSPITALS",
        "INSTRUM.": "INSTRUMENTS",
        "COMMU.": "COMMUNICATIONS",
        "ELECTRICA": "ELECTRICALS",
        "DIAGNO.": "DIAGNOSTICS",
        "LIFESTY.": "LIFESTYLE",
        "INTEGRAT": "INTEGRATED",
        "HEALTHCAR": "HEALTHCARE",
        "LABORATO": "LABORATORIES",
        "ACCESSOR.": "ACCESSORIES",
        "MECHATRO": "MECHATRONICS",
        "SURREND.": "SURRENDRA",
        "STAIN.": "STAINLESS",
        "PHOTOVOL.": "PHOTOVOLTAIC",
        "INF.": "INFRASTRUCTURE",
        "HSG.": "HOUSING",
        "FIN.": "FINANCE",
        "PRECIS.": "PRECISION",
        "SER.": "SERVICES",
        "HEA": "HEALTH",
        "EL": "ELECTRICAL",
        "ENE.": "ENERGY",
        "SOLUT.": "SOLUTIONS",
        "INFOSOLUT": "INFOSOLUTIONS",
        "AERO.": "AEROSPACE",
        "EQUIP.": "EQUIPMENT",
        "ANALYT.": "ANALYTICS",
        "FINTRADE": "FINTRADE",
        "BIOREF.": "BIOREFINERY",
        "INFRASTR.": "INFRASTRUCTURE",
        "ADV.": "ADVISORS",
        "PETR.": "PETROLEUM",
    }
    for abbr, full in abbreviations.items():
        s = s.replace(abbr, full)

    # Remove trailing dots (truncated names)
    s = re.sub(r'\.\s*$', '', s)
    # Remove extra whitespace
    s = re.sub(r'\s+', ' ', s).strip()

    return s


def fuzzy_match(ipo_name: str, kite_names: list[str], limit: int = 3) -> list[tuple]:
    """
    Find the best fuzzy matches for an IPO stock name among Kite instruments.
    Uses a combination of token_sort_ratio and token_set_ratio for best results.
    Returns list of (matched_name, score).
    """
    normalized = normalize(ipo_name)

    # Use token_set_ratio — best for partial / abbreviated names
    results = process.extract(
        normalized,
        kite_names,
        scorer=fuzz.token_set_ratio,
        limit=limit,
    )
    return results


def main():
    print("=" * 70)
    print("  Fuzzy Match: IPO Stocks → Kite Trading Symbols")
    print("=" * 70)
    print()

    # Load data
    kite_data = load_kite_instruments(KITE_JSON)
    ipo_stocks = load_ipo_stocks(IPO_CSV)

    kite_names = list(kite_data.keys())
    # Pre-normalize kite names for better matching
    kite_names_normalized = [normalize(n) for n in kite_names]
    # Map normalized → original
    norm_to_orig = dict(zip(kite_names_normalized, kite_names))

    print(f"  📊 IPO stocks to match: {len(ipo_stocks)}")
    print(f"  📋 Kite instruments:    {len(kite_names)}")
    print()

    # Match each IPO stock
    matched_results = []
    no_match_count = 0

    header = (
        f"{'#':<4} {'IPO Stock Name':<30} {'Score':<7} "
        f"{'Kite Match':<35} {'Symbol':<15} {'Exch':<5} {'Year':<5}"
    )
    print(header)
    print("-" * len(header))

    for i, stock in enumerate(ipo_stocks, 1):
        ipo_name = stock["Stock Name"]

        # Check manual overrides first
        if ipo_name in MANUAL_OVERRIDES:
            symbol, exchange = MANUAL_OVERRIDES[ipo_name]
            best_match_orig = f"[OVERRIDE]"
            best_score = 100
        else:
            # Fuzzy match against normalized kite names
            matches = fuzzy_match(ipo_name, kite_names_normalized, limit=3)

            best_match_norm, best_score, *_ = matches[0]
            best_match_orig = norm_to_orig[best_match_norm]

            if best_score >= MIN_SCORE:
                info = kite_data[best_match_orig]
                symbol = info["symbol"]
                exchange = info["exchange"]
            else:
                symbol = "NOT_FOUND"
                exchange = "-"
                no_match_count += 1

        print(
            f"{i:<4} {ipo_name:<30} {best_score:<7} "
            f"{best_match_orig:<35} {symbol:<15} {exchange:<5} {stock['Year']:<5}"
        )

        matched_results.append({
            "Stock Name": ipo_name,
            "Symbol": symbol,
            "Exchange": exchange,
            "Match Score": best_score,
            "Kite Match Name": best_match_orig if best_score >= MIN_SCORE else "",
            "Listing Date": stock["Listing Date"],
            "Year": stock["Year"],
            "IPO MCap (Cr)": stock["IPO MCap (Cr)"],
            "IPO Price": stock["IPO Price"],
            "Current Price": stock["Current Price"],
            "% Change": stock["% Change"],
        })

    print()
    print(f"  ✅ Matched:    {len(ipo_stocks) - no_match_count} / {len(ipo_stocks)}")
    print(f"  ❌ No match:   {no_match_count} / {len(ipo_stocks)}")
    print()

    # ── Save to CSV ──
    fieldnames = [
        "Stock Name", "Symbol", "Exchange", "Match Score", "Kite Match Name",
        "Listing Date", "Year", "IPO MCap (Cr)", "IPO Price",
        "Current Price", "% Change",
    ]
    with open(OUTPUT_CSV, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(matched_results)

    print(f"  📁 Results saved to: {OUTPUT_CSV}")
    print()

    # ── Print NOT_FOUND stocks for manual review ──
    not_found = [r for r in matched_results if r["Symbol"] == "NOT_FOUND"]
    if not_found:
        print("  ⚠  Stocks that could NOT be matched (review manually):")
        print("  " + "-" * 50)
        for r in not_found:
            print(f"    • {r['Stock Name']} (Year: {r['Year']})")
        print()


if __name__ == "__main__":
    main()
