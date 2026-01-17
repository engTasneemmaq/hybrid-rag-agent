"""
Helper script to download PDFs from URLs provided by setup_data.py.
Downloads 10-K reports for AAPL, MSFT, and TSLA.
"""
import requests
from pathlib import Path
import sys

PDF_DIR = Path("data/pdfs")
PDF_DIR.mkdir(parents=True, exist_ok=True)

PDF_URLS = {
    "AAPL": "https://s2.q4cdn.com/470004039/files/doc_earnings/2023/q4/filing/_10-K-Q4-2023-As-Filed.pdf",
    "MSFT": "https://microsoft.gcs-web.com/static-files/e2931fdb-9823-4130-b2a8-f6b8db0b15a9",
    "TSLA": "https://ir.tesla.com/_flysystem/s3/sec/000162828024002390/tsla-20231231-gen.pdf"
}

def download_pdf(ticker: str, url: str, output_path: Path):
    """Download a PDF from URL."""
    print(f"Downloading {ticker} 10-K from {url[:60]}...")
    try:
        response = requests.get(url, timeout=60, stream=True)
        response.raise_for_status()
        
        with open(output_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
        
        print(f"✅ Saved to {output_path}")
        return True
    except Exception as e:
        print(f"❌ Failed to download {ticker}: {e}")
        return False

if __name__ == "__main__":
    print("📄 Downloading 10-K PDFs...")
    print("Note: If URLs expire, search for 'Company Name 2023 Annual Report 10-K' on Google.\n")
    
    success_count = 0
    for ticker, url in PDF_URLS.items():
        output_path = PDF_DIR / f"{ticker}_2023_10K.pdf"
        if download_pdf(ticker, url, output_path):
            success_count += 1
    
    print(f"\n✅ Downloaded {success_count}/{len(PDF_URLS)} PDFs")
    if success_count < len(PDF_URLS):
        print("⚠️  Some downloads failed. You may need to download manually.")
        sys.exit(1)
