import sys
import os
# Add project root to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))

import asyncio
import csv
import logging
import time
from datetime import date, timedelta, datetime
from typing import List, Dict, Any

from semanticscholar import SemanticScholar
from src.services.arxiv.client import ArxivClient
from src.schemas.paper import ArxivPaper

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class DatasetBuilder:
    def __init__(self):
        self.arxiv_client = ArxivClient()
        self.sch = SemanticScholar(timeout=10)
        
    def fetch_historical_papers(self, days_ago_start: int, days_ago_end: int, max_papers: int = 500) -> List[ArxivPaper]:
        """Fetch papers from a specific historical window."""
        end_date = date.today() - timedelta(days=days_ago_end)
        start_date = date.today() - timedelta(days=days_ago_start)
        
        logger.info(f"Fetching arXiv papers from {start_date} to {end_date}...")
        
        categories = ["cs.AI", "cs.LG", "cs.CL", "cs.CV"] 
        cat_queries = [f"cat:{cat}" for cat in categories]
        cat_part = f"({' OR '.join(cat_queries)})"
        
        start_str = start_date.strftime("%Y%m%d") + "0000"
        end_str = end_date.strftime("%Y%m%d") + "2359"
        date_part = f"submittedDate:[{start_str} TO {end_str}]"
        
        query = f"{cat_part} AND {date_part}"
        
        result = self.arxiv_client._fetch_with_pagination(query, max_results=max_papers)
        logger.info(f"Fetched {len(result.papers)} papers from arXiv.")
        return result.papers

    def get_citation_counts(self, papers: List[ArxivPaper]) -> Dict[str, int]:
        """Get citation counts from Semantic Scholar with robust rate limiting."""
        logger.info("Fetching citation counts from Semantic Scholar...")
        
        lookup_map = {f"arXiv:{p.arxiv_id}": p.arxiv_id for p in papers}
        search_ids = list(lookup_map.keys())
        citation_map = {}
        
        batch_size = 100
        total_batches = (len(search_ids) + batch_size - 1) // batch_size
        
        for i in range(0, len(search_ids), batch_size):
            batch = search_ids[i:i+batch_size]
            current_batch_num = i // batch_size + 1
            
            retries = 3
            backoff = 10
            
            while retries > 0:
                try:
                    logger.info(f"Processing Semantic Scholar batch {current_batch_num}/{total_batches}...")
                    results = self.sch.get_papers(batch, fields=['citationCount', 'title', 'externalIds'])
                    
                    for res in results:
                        if res and res.externalIds and 'ArXiv' in res.externalIds:
                             aid = res.externalIds['ArXiv']
                             if res.citationCount is not None:
                                citation_map[aid] = res.citationCount
                    
                    # Success - sleep briefly to be nice
                    time.sleep(2) 
                    break
                    
                except Exception as e:
                    is_rate_limit = "429" in str(e) or "Too Many Requests" in str(e)
                    if is_rate_limit:
                        logger.warning(f"Rate limit hit. Sleeping {backoff}s...")
                        time.sleep(backoff)
                        backoff *= 2  # Exponential backoff
                        retries -= 1
                    else:
                        logger.error(f"Error checking batch {i}: {e}")
                        break # Skip other errors
            
        return citation_map

    def save_to_csv(self, papers: List[ArxivPaper], citation_map: Dict[str, int], filename: str):
        """Save chunk to CSV (overwrite if exists)."""
        os.makedirs(os.path.dirname(filename), exist_ok=True)
        
        logger.info(f"Saving {len(papers)} records to {filename}...")
        
        with open(filename, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow([
                'arxiv_id', 'title', 'abstract', 'authors', 
                'primary_category', 'all_categories', 'published_at', 'citation_count'
            ])
            
            count_with_citations = 0
            for p in papers:
                c_count = citation_map.get(p.arxiv_id, 0)
                if p.arxiv_id in citation_map:
                    count_with_citations += 1
                
                authors_str = "|".join(p.authors)
                cats_str = "|".join(p.categories)
                primary_cat = p.categories[0] if p.categories else ""
                
                writer.writerow([
                    p.arxiv_id, p.title, p.abstract, authors_str,
                    primary_cat, cats_str, p.published_at.isoformat(), c_count
                ])
                
        logger.info(f"Saved chunk. Found citation data for {count_with_citations}/{len(papers)} papers.")

def combine_chunks(output_path: str, chunks_dir: str):
    """Combine all chunk CSVs into one."""
    logger.info("Combining chunks...")
    if not os.path.exists(chunks_dir):
        logger.warning("Chunks directory not found.")
        return

    all_files = [os.path.join(chunks_dir, f) for f in os.listdir(chunks_dir) if f.endswith(".csv")]
    all_files.sort() 
    
    if not all_files:
        logger.warning("No chunks found.")
        return

    header = [
        'arxiv_id', 'title', 'abstract', 'authors', 
        'primary_category', 'all_categories', 'published_at', 'citation_count'
    ]
    
    with open(output_path, 'w', newline='', encoding='utf-8') as f_out:
        writer = csv.writer(f_out)
        writer.writerow(header)
        
        seen_ids = set()
        
        for fp in all_files:
            try:
                with open(fp, 'r', encoding='utf-8') as f_in:
                    reader = csv.reader(f_in)
                    chunk_header = next(reader, None)
                    if not chunk_header: continue
                    
                    for row in reader:
                        # row[0] is arxiv_id
                        if row and row[0] not in seen_ids:
                            writer.writerow(row)
                            seen_ids.add(row[0])
            except Exception as e:
                logger.error(f"Error reading chunk {fp}: {e}")
                
    logger.info(f"Combined {len(seen_ids)} unique papers into {output_path}")

def main():
    builder = DatasetBuilder()
    
    # Define paths
    base_dir = os.path.dirname(os.path.abspath(__file__))
    data_dir = os.path.join(base_dir, "../data")
    chunks_dir = os.path.join(data_dir, "chunks")
    output_path = os.path.join(data_dir, "eda_papers.csv")
    
    os.makedirs(chunks_dir, exist_ok=True)
    
    # Iterate from 365 days ago to 0 days (Today) in chunks of 7 days (Weekly)
    start_days_ago = 365
    end_days_ago = 0
    step = 7
    
    current_days_ago = start_days_ago
    
    while current_days_ago > end_days_ago:
        chunk_start = current_days_ago
        chunk_end = max(current_days_ago - step, end_days_ago)
        
        chunk_filename = os.path.join(chunks_dir, f"papers_{chunk_start}_{chunk_end}.csv")
        
        if os.path.exists(chunk_filename):
            logger.info(f"Skipping chunk {chunk_start}-{chunk_end} (already exists).")
            current_days_ago -= step
            continue
            
        logger.info(f"=== Processing Week: {chunk_start} to {chunk_end} days ago ===")
        
        try:
            # Fetch ALL papers for this week (up to 5000)
            papers = builder.fetch_historical_papers(
                days_ago_start=chunk_start, 
                days_ago_end=chunk_end, 
                max_papers=5000 
            )
            
            if papers:
                logger.info(f"Found {len(papers)} papers. Fetching citations...")
                citations = builder.get_citation_counts(papers)
                builder.save_to_csv(papers, citations, chunk_filename)
            else:
                logger.info("No papers found for this chunk.")
                # Save empty file to avoid re-fetching zero results next time
                # Or just skip. Saving empty file is safer for "completeness" check.
                # But our csv structure expects header.
                builder.save_to_csv([], {}, chunk_filename)
            
            # Rate limit politeness
            logger.info("Week done. Sleeping 5s...")
            time.sleep(5)
            
        except Exception as e:
            logger.error(f"Error processing chunk {chunk_start}-{chunk_end}: {e}")
        
        current_days_ago -= step

    # Combine all at the end
    combine_chunks(output_path, chunks_dir)

if __name__ == "__main__":
    main()
