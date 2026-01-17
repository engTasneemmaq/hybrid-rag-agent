# PDF ingestion - extracts text and tables from 10-K PDFs
import pdfplumber
import logging
from pathlib import Path
from typing import List, Dict
import json

logger = logging.getLogger(__name__)

class PDFIngester:
    
    def __init__(self, pdf_dir: Path):
        self.pdf_dir = pdf_dir
    
    def extract_chunks(self, pdf_path: Path) -> List[Dict]:
        chunks = []
        try:
            with pdfplumber.open(pdf_path) as pdf:
                filename = pdf_path.stem
                company = self._extract_company(filename)
                year = self._extract_year(filename)
                
                for page_num, page in enumerate(pdf.pages, start=1):
                    text = page.extract_text()
                    if text and text.strip():
                        chunks.append({
                            "content": text.strip(),
                            "chunk_type": "text",
                            "page": page_num,
                            "pdf_filename": pdf_path.name,
                            "company": company,
                            "year": year
                        })
                    
                    tables = page.extract_tables()
                    for table_idx, table in enumerate(tables):
                        if table:
                            table_text = self._table_to_markdown(table)
                            if table_text:
                                chunks.append({
                                    "content": table_text,
                                    "chunk_type": "table",
                                    "page": page_num,
                                    "table_index": table_idx,
                                    "pdf_filename": pdf_path.name,
                                    "company": company,
                                    "year": year
                                })
            
            logger.info(f"Extracted {len(chunks)} chunks from {pdf_path.name}")
            return chunks
        
        except Exception as e:
            logger.error(f"Error extracting from {pdf_path}: {e}")
            return []
    
    def _extract_company(self, filename: str) -> str:
        tickers = ["AAPL", "MSFT", "TSLA", "APPLE", "MICROSOFT", "TESLA"]
        filename_upper = filename.upper()
        for ticker in tickers:
            if ticker in filename_upper:
                return ticker
        return "UNKNOWN"
    
    def _extract_year(self, filename: str) -> str:
        import re
        match = re.search(r"20\d{2}", filename)
        if match:
            return match.group(0)
        return "2023"
    
    def _table_to_markdown(self, table: List[List]) -> str:
        if not table or len(table) < 2:
            return ""
        
        lines = []
        header = table[0]
        lines.append("| " + " | ".join(str(cell) if cell else "" for cell in header) + " |")
        lines.append("| " + " | ".join(["---"] * len(header)) + " |")
        
        for row in table[1:]:
            if row:
                lines.append("| " + " | ".join(str(cell) if cell else "" for cell in row) + " |")
        
        return "\n".join(lines)
    
    def ingest_all_pdfs(self) -> List[Dict]:
        all_chunks = []
        pdf_files = list(self.pdf_dir.glob("*.pdf"))
        
        if not pdf_files:
            logger.warning(f"No PDF files found in {self.pdf_dir}")
            return []
        
        for pdf_path in pdf_files:
            chunks = self.extract_chunks(pdf_path)
            all_chunks.extend(chunks)
        
        logger.info(f"Total chunks extracted: {len(all_chunks)}")
        return all_chunks

def chunk_text_semantically(text: str, max_chunk_size: int = 1000, overlap: int = 200) -> List[str]:
    import re
    sentences = re.split(r'(?<=[.!?])\s+', text)
    
    chunks = []
    current_chunk = []
    current_size = 0
    
    for sentence in sentences:
        sentence_size = len(sentence)
        
        if current_size + sentence_size > max_chunk_size and current_chunk:
            chunks.append(" ".join(current_chunk))
            overlap_sentences = current_chunk[-min(len(current_chunk), overlap // 50):]
            current_chunk = overlap_sentences + [sentence]
            current_size = sum(len(s) for s in current_chunk)
        else:
            current_chunk.append(sentence)
            current_size += sentence_size
    
    if current_chunk:
        chunks.append(" ".join(current_chunk))
    
    return chunks

if __name__ == "__main__":
    import sys
    import json
    logging.basicConfig(level=logging.INFO)
    
    from config import PDF_DIR, DATA_DIR
    from retriever import VectorStore
    
    ingester = PDFIngester(PDF_DIR)
    chunks = ingester.ingest_all_pdfs()
    
    if chunks:
        chunks_file = DATA_DIR / "chunks.json"
        with open(chunks_file, 'w') as f:
            json.dump(chunks, f, indent=2)
        print(f"Saved {len(chunks)} chunks to {chunks_file}")
        
        vector_store = VectorStore()
        vector_store.add_chunks(chunks)
        vector_store.save()
        print(f"Ingested {len(chunks)} chunks into vector store")
    else:
        print("No chunks extracted. Make sure PDFs are in data/pdfs/")
        sys.exit(1)
