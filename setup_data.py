import sqlite3
import pandas as pd
import numpy as np
import os
from datetime import datetime, timedelta

# --- Configuration ---
DB_NAME = "finance.db"
START_DATE = "2023-01-01"
END_DATE = "2023-12-31"
TICKERS = ["AAPL", "MSFT", "TSLA"]

def generate_stock_data():
    """Generates realistic-looking random stock data for 2023."""
    print(f"Generating {DB_NAME}...")
    
    np.random.seed(42)
    # Date range
    dates = pd.date_range(start=START_DATE, end=END_DATE, freq='B') # Business days
    
    data = []
    
    # Baselines for simulation
    baselines = {
        "AAPL": 150.0,
        "MSFT": 240.0,
        "TSLA": 120.0
    }
    
    for ticker in TICKERS:
        price = baselines[ticker]
        for date in dates:
            # Random walk
            change = np.random.normal(0, 2.5)
            price += change
            volume = np.random.randint(1_000_000, 10_000_000)
            
            data.append({
                "symbol": ticker,
                "date": date.strftime("%Y-%m-%d"),
                "open": round(price - np.random.random(), 2),
                "close": round(price + np.random.random(), 2),
                "volume": volume
            })

    df = pd.DataFrame(data)
    
    # Save to SQLite
    conn = sqlite3.connect(DB_NAME)
    df.to_sql("stock_prices", conn, if_exists="replace", index=False)
    conn.close()
    
    print(f"✅ Database created: {DB_NAME}")
    print(f"   Table: stock_prices (symbol, date, open, close, volume)")
    print(f"   Rows: {len(df)}")

def print_pdf_instructions():
    print("\n--- 📄 PDF Download Instructions ---")
    print("Please download the following 2023 10-K reports for your Knowledge Base:")
    print("1. Apple (AAPL): https://s2.q4cdn.com/470004039/files/doc_earnings/2023/q4/filing/_10-K-Q4-2023-As-Filed.pdf")
    print("2. Microsoft (MSFT): https://microsoft.gcs-web.com/static-files/e2931fdb-9823-4130-b2a8-f6b8db0b15a9")
    print("3. Tesla (TSLA): https://ir.tesla.com/_flysystem/s3/sec/000162828024002390/tsla-20231231-gen.pdf")
    print("\n⚠️  NOTE: If links expire, search for 'Company Name 2023 Annual Report 10-K' on Google.")

if __name__ == "__main__":
    generate_stock_data()
    print_pdf_instructions()