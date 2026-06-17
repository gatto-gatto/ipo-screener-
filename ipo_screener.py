#!/usr/bin/env python3
"""
IPO Screener
=============
Loads IPO data from 2023, 2024, and 2025 Excel files, maps names to Yahoo Finance
symbols using Kite instruments, fetches the LTP, and checks if LTP is within
±5% of the first-day high (NSE High).
"""

import os
import re
import json
import csv
import pandas as pd
import yfinance as yf
from thefuzz import process, fuzz

# --- File Paths ---
EXCEL_FILES = {
    2023: "ipo_data2023.xlsx",
    2024: "ipo_data2024.xlsx",
    2025: "ipo_data2025.xlsx"
}
KITE_JSON = "kite_instruments.json"
OUTPUT_CSV = "screened_ipos.csv"

# --- Manual Mapping Overrides ---
# For names that can't be resolved easily or have unique parent/brand/ticker names.
MANUAL_MAP = {
    'Schloss Bangalore': ('THELEELA', 'NSE'),
    'Zinka Logistics Solutions': ('BLACKBUCK', 'NSE'),
    'Credo Brands Marketing': ('MUFTI', 'NSE'),
    'Anand Rathi Share & Stock Brokers': ('ARSSBL', 'NSE'),
    'Anand Rathi Share and Stock Brokers': ('ARSSBL', 'NSE'),
    'Highway Infrastructure': ('VERTIS', 'NSE'),
    'Highway Infrastructure Trust': ('VERTIS', 'NSE'),
    'IKIO Lighting': ('IKIO', 'NSE'),
    'Premier Energies': ('PREMIER', 'NSE'),
    'Hyundai Motor India': ('HYUNDAI', 'NSE'),
    'Ola Electric Mobility': ('OLAELEC', 'NSE'),
    'Swiggy': ('SWIGGY', 'NSE'),
    'Bansal Wire Industries': ('BANSALWIRE', 'NSE'),
    'Platinum Industries': ('PLATIND', 'NSE'),
    'Jinkushal Industries': ('JKIPL', 'NSE'),
    'BMW Ventures': ('BMWVENTLTD', 'BSE'),
    'Mangal Electrical Industries': ('MBEL', 'NSE'),
    'Ellenbarrie Industrial Gases': ('ELLEN', 'NSE'),
    'Belrise Industries': ('BELRISE', 'NSE'),
    'Rosmerta Digital Services': ('ROSMERTA', 'NSE'),
    'Indian Renewable Energy Development Agency': ('IREDA', 'NSE'),
}

def normalize(name: str) -> str:
    """Normalize company name to improve fuzzy matching accuracy."""
    s = str(name).strip().upper()
    abbreviations = {
        'TECH.': 'TECHNOLOGIES', 'TECHNOL.': 'TECHNOLOGIES', 'ENGG.': 'ENGINEERING',
        'PHARMA.': 'PHARMACEUTICALS', 'INFRA.': 'INFRASTRUCTURE', 'INDUSTR': 'INDUSTRIES',
        'FINAN': 'FINANCE', 'FINANC.': 'FINANCE', 'HOSPIT.': 'HOSPITALS',
        'INSTRUM.': 'INSTRUMENTS', 'COMMU.': 'COMMUNICATIONS', 'ELECTRICA': 'ELECTRICALS',
        'DIAGNO.': 'DIAGNOSTICS', 'LIFESTY.': 'LIFESTYLE', 'INTEGRAT': 'INTEGRATED',
        'HEALTHCAR': 'HEALTHCARE', 'LABORATO': 'LABORATORIES', 'ACCESSOR.': 'ACCESSORIES',
        'MECHATRO': 'MECHATRONICS', 'SURREND.': 'SURRENDRA', 'STAIN.': 'STAINLESS',
        'PHOTOVOL.': 'PHOTOVOLTAIC', 'INF.': 'INFRASTRUCTURE', 'HSG.': 'HOUSING',
        'FIN.': 'FINANCE', 'PRECIS.': 'PRECISION', 'SER.': 'SERVICES',
        'HEA': 'HEALTH', 'EL': 'ELECTRICAL', 'ENE.': 'ENERGY', 'SOLUT.': 'SOLUTIONS',
        'INFOSOLUT': 'INFOSOLUTIONS', 'AERO.': 'AEROSPACE', 'EQUIP.': 'EQUIPMENT',
        'ANALYT.': 'ANALYTICS', 'BIOREF.': 'BIOREFINERY', 'INFRASTR.': 'INFRASTRUCTURE',
        'ADV.': 'ADVISORS', 'PETR.': 'PETROLEUM', 'LTD': 'LIMITED', 'LTD.': 'LIMITED',
        'CORP': 'CORPORATION', 'CORP.': 'CORPORATION', 'CO': 'COMPANY', 'CO.': 'COMPANY'
    }
    for abbr, full in abbreviations.items():
        s = re.sub(rf'\b{re.escape(abbr)}\b', full, s)
    s = re.sub(r'\.\s*$', '', s)
    s = re.sub(r'\s+', ' ', s).strip()
    return s

def clean_price(val) -> float:
    """Clean and parse price strings (e.g. ₹1,087.40) to float."""
    if pd.isna(val):
        return float('nan')
    try:
        clean_str = re.sub(r'[^\d.]', '', str(val))
        return float(clean_str)
    except Exception:
        return float('nan')

def get_ticker_suffix(exchange: str) -> str:
    """Return the Yahoo Finance suffix based on the exchange name."""
    if str(exchange).upper() == 'BSE':
        return '.BO'
    return '.NS'

def main():
    print("=" * 70)
    print("       🚀 IPO Screener (Yahoo Finance LTP vs First Day High) 🚀")
    print("=" * 70)

    # 1. Load Kite instruments data
    if not os.path.exists(KITE_JSON):
        print(f"❌ Error: {KITE_JSON} not found!")
        return

    print("📖 Loading Kite instruments...")
    with open(KITE_JSON, 'r', encoding='utf-8') as f:
        kite_data = json.load(f)['data']

    # Pre-normalize Kite names for fuzzy matching
    kite_names = list(kite_data.keys())
    kite_names_norm = [normalize(n) for n in kite_names]
    norm_to_orig = dict(zip(kite_names_norm, kite_names))

    # 2. Load and parse Excel files
    stocks = []
    print("📊 Parsing Excel files...")
    for year, filepath in EXCEL_FILES.items():
        if not os.path.exists(filepath):
            print(f"⚠️ Warning: Excel file for {year} ({filepath}) not found. Skipping...")
            continue
        
        df = pd.read_excel(filepath)
        for idx, row in df.iterrows():
            name = row['IPO Name']
            if pd.isna(name):
                continue
            
            raw_high = row.get('NSE High', float('nan'))
            first_day_high = clean_price(raw_high)
            
            stocks.append({
                'Name': name,
                'Year': year,
                'Excel High': first_day_high,
                'RowIdx': idx
            })
    
    print(f"✅ Loaded {len(stocks)} IPO stocks from Excel.")

    # 3. Map company names to symbols
    print("🔍 Mapping company names to symbols...")
    mapped_stocks = []
    unmapped_count = 0

    for s in stocks:
        name = s['Name']
        symbol = None
        exchange = 'NSE'

        # Check manual overrides
        if name in MANUAL_MAP:
            symbol, exchange = MANUAL_MAP[name]
        else:
            # Fuzzy match
            norm_name = normalize(name)
            matches = process.extract(norm_name, kite_names_norm, scorer=fuzz.token_set_ratio, limit=1)
            if matches and matches[0][1] >= 75:
                best_match_norm = matches[0][0]
                orig_name = norm_to_orig[best_match_norm]
                info = kite_data[orig_name]
                symbol = info['symbol']
                exchange = info['exchange']
            else:
                unmapped_count += 1
                print(f"⚠️ Could not map: {name}")
                continue

        # Clean symbol by stripping trade category suffixes (e.g. -BE, -SM, -ST) for Yahoo Finance lookup
        clean_symbol = symbol.split('-')[0]
        ticker = f"{clean_symbol}{get_ticker_suffix(exchange)}"
        
        mapped_stocks.append({
            'Name': name,
            'Year': s['Year'],
            'Excel High': s['Excel High'],
            'Symbol': symbol,
            'CleanSymbol': clean_symbol,
            'Exchange': exchange,
            'Ticker': ticker
        })

    print(f"📊 Symbol Mapping Summary: {len(mapped_stocks)} successfully mapped, {unmapped_count} unmapped.")

    if not mapped_stocks:
        print("❌ No stocks mapped. Exiting...")
        return

    # Deduplicate tickers for API request
    all_tickers = list(set([s['Ticker'] for s in mapped_stocks]))
    
    # 4. Fetch LTP for all tickers in a single batch
    print("\n📥 Fetching latest prices (LTP) from Yahoo Finance...")
    try:
        data = yf.download(all_tickers, period='5d', progress=False)
        close_df = data['Close'] if len(all_tickers) > 1 else pd.DataFrame({all_tickers[0]: data['Close']})
    except Exception as e:
        print(f"❌ Error downloading batch prices from yfinance: {e}")
        return

    # Map ticker to its LTP
    ticker_ltp = {}
    for ticker in all_tickers:
        if ticker in close_df:
            series = close_df[ticker].dropna()
            if not series.empty:
                ticker_ltp[ticker] = float(series.iloc[-1])
            else:
                ticker_ltp[ticker] = float('nan')
        else:
            ticker_ltp[ticker] = float('nan')

    # 5. Process and Screen
    print("\n🔍 Screening stocks within ±5% of first-day high...")
    screened_results = []
    failed_ticker_lookups = []

    for s in mapped_stocks:
        ticker = s['Ticker']
        name = s['Name']
        first_day_high = s['Excel High']
        ltp = ticker_ltp.get(ticker, float('nan'))

        if pd.isna(ltp) or ltp <= 0:
            # Try a single fallback lookup in case batch missed it
            try:
                single_ticker = yf.Ticker(ticker)
                hist = single_ticker.history(period='5d')
                if not hist.empty:
                    ltp = float(hist['Close'].dropna().iloc[-1])
            except Exception:
                pass

        if pd.isna(ltp) or ltp <= 0:
            failed_ticker_lookups.append(f"{name} ({ticker})")
            continue

        # Check if first-day high is missing and fetch dynamically
        recovered = False
        if pd.isna(first_day_high):
            try:
                single_ticker = yf.Ticker(ticker)
                hist = single_ticker.history(period='max')
                if not hist.empty:
                    first_day_high = float(hist['High'].iloc[0])
                    recovered = True
            except Exception as e:
                pass

        if pd.isna(first_day_high) or first_day_high <= 0:
            # Skip if we still don't have first-day high
            continue

        # Calculate deviation percentage
        deviation = ((ltp - first_day_high) / first_day_high) * 100
        
        # Check if deviation is within ±5%
        if -5.0 <= deviation <= 5.0:
            screened_results.append({
                'Name': name,
                'Symbol': s['Symbol'],
                'Exchange': s['Exchange'],
                'Year': s['Year'],
                'First Day High': round(first_day_high, 2),
                'LTP': round(ltp, 2),
                'Deviation %': round(deviation, 2),
                'Recovered High': "Yes" if recovered else "No"
            })

    # Sort results by Year (descending) then Name
    screened_results = sorted(screened_results, key=lambda x: (x['Year'], x['Name']), reverse=True)

    # 6. Output Results
    print("\n" + "=" * 100)
    print(f"🎯 SCREENED STOCKS WITHIN ±5% OF FIRST-DAY HIGH (Total Matches: {len(screened_results)})")
    print("=" * 100)
    header = f"{'Stock Name':<35} {'Symbol':<15} {'Year':<6} {'First Day High':<16} {'LTP':<10} {'Dev %':<8} {'Recovered':<10}"
    print(header)
    print("-" * len(header))
    
    for r in screened_results:
        # Wrap stock name in Green ANSI code (\033[92m ... \033[0m)
        green_name = f"\033[92m{r['Name']:<35}\033[0m"
        print(f"{green_name} {r['Symbol']:<15} {r['Year']:<6} {r['First Day High']:<16} {r['LTP']:<10} {r['Deviation %']:+7.2f}% {r['Recovered High']:<10}")
    print("=" * 100)

    # Comma-separated list of matched symbols below the table
    if screened_results:
        symbols_list = [r['Symbol'] for r in screened_results]
        symbols_str = ", ".join(symbols_list)
        print("\n📋 Comma-separated Matched Symbols:")
        print(symbols_str)
        print()

    # Output failed lookups summary (for info only)
    if failed_ticker_lookups:
        print(f"⚠️ Could not retrieve prices for {len(failed_ticker_lookups)} tickers on Yahoo Finance (e.g. delisted/unsupported):")
        print(", ".join(failed_ticker_lookups[:10]))
        if len(failed_ticker_lookups) > 10:
            print(f"... and {len(failed_ticker_lookups) - 10} more.")

    # Save to CSV
    if screened_results:
        with open(OUTPUT_CSV, 'w', newline='', encoding='utf-8') as f:
            fieldnames = ['Name', 'Symbol', 'Exchange', 'Year', 'First Day High', 'LTP', 'Deviation %', 'Recovered High']
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(screened_results)
        print(f"\n💾 Results saved successfully to: {OUTPUT_CSV}")
    else:
        print("\nℹ️ No stocks matched the screening criteria.")

if __name__ == '__main__':
    main()
