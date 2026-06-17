# IPO Screener & Analyzer

This project contains tools to load, process, and screen Initial Public Offering (IPO) stocks in the Indian market (NSE and BSE) for the years **2023, 2024, and 2025**.

It compares real-time Last Traded Prices (LTP) fetched via the Yahoo Finance API against the stock's first-day trading high to identify interesting setup opportunities.

---

## 🚀 Features

1. **IPO Screener (`ipo_screener.py`)**:
   - Loads historical IPO records from Excel sheets (`2023`, `2024`, and `2025`).
   - Normalizes stock names and fuzzy matches them to trading symbols using Kite's instrument master.
   - Automatically cleans transaction/trade categories (stripping `-BE`, `-SM`, `-ST` etc.) for correct Yahoo Finance resolution.
   - Dynamically recovers missing first-day highs (e.g. if NaN in Excel) from Yahoo Finance's historical data.
   - Fetches current LTPs concurrently in a fast batch request.
   - Filters and highlights stocks trading **within ±5% of their first-day high**.
   - Outputs a beautifully formatted table (with green stock names) and a comma-separated list of symbols.
   - Saves results to `screened_ipos.csv`.

2. **Symbol Matcher (`fuzzy_match_symbols.py`)**:
   - Matches raw company names against Kite instruments to generate mapping files.

---

## 📦 Installation & Setup

Make sure you have Python 3 installed. You can install the required dependencies using `pip`:

```bash
pip install pandas openpyxl yfinance thefuzz python-Levenshtein
```

---

## 🏃 How to Run

Simply execute the main screener script:

```bash
python3 ipo_screener.py
```

### Output Example:
```text
======================================================================
       🚀 IPO Screener (Yahoo Finance LTP vs First Day High) 🚀
======================================================================
📖 Loading Kite instruments...
📊 Parsing Excel files...
...
====================================================================================================
🎯 SCREENED STOCKS WITHIN ±5% OF FIRST-DAY HIGH (Total Matches: 23)
====================================================================================================
Stock Name                          Symbol          Year   First Day High   LTP        Dev %    Recovered 
----------------------------------------------------------------------------------------------------------
WeWork India Management             WEWORK          2025   650.15           649.9        -0.04% No        
Tata Capital                        TATACAP         2025   333.0            337.1        +1.23% No        
...
====================================================================================================

📋 Comma-separated Matched Symbols:
WEWORK, TATACAP, SMARTWORKS, SCODATUBES, THELEELA, SAMBHV, SAATVIKGL, ...

💾 Results saved successfully to: screened_ipos.csv
```

---

## 📁 File Structure

* **`ipo_screener.py`**: The main executable screener.
* **`ipo_data2023.xlsx`**, **`ipo_data2024.xlsx`**, **`ipo_data2025.xlsx`**: Raw Excel files containing scraped IPO listings data.
* **`kite_instruments.json`**: Kite instruments definition dictionary mapping full company names to exchange symbols.
* **`screened_ipos.csv`**: Auto-generated output containing the list of screened stocks.
# ipo-screener-
