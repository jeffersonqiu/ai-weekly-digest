import csv
import os
import re
import logging
from datetime import date, timedelta, datetime

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def merge_chunks():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    data_dir = os.path.join(base_dir, "../data")
    chunks_dir = os.path.join(data_dir, "chunks")
    output_path = os.path.join(data_dir, "eda_papers.csv") # Overwrite the default one or new name? User said "combine chunks".
    
    if not os.path.exists(chunks_dir):
        logger.warning(f"Chunks directory not found: {chunks_dir}")
        return

    all_files = [f for f in os.listdir(chunks_dir) if f.endswith(".csv")]
    all_files.sort() # Sort by name (which puts 100 before 20... wait. integer sorting needed? filenames are papers_365_358.csv)
    
    # regex to parse filename
    # papers_365_358.csv
    pattern = re.compile(r"papers_(\d+)_(\d+)\.csv")
    
    header = [
        'arxiv_id', 'title', 'abstract', 'authors', 
        'primary_category', 'all_categories', 'published_at', 'citation_count',
        'chunk_start_days_ago', 'chunk_end_days_ago', 'chunk_start_date', 'chunk_end_date'
    ]
    
    logger.info(f"combining {len(all_files)} chunks into {output_path}...")
    
    seen_ids = set()
    rows_written = 0
    
    with open(output_path, 'w', newline='', encoding='utf-8') as f_out:
        writer = csv.writer(f_out)
        writer.writerow(header)
        
        for fname in all_files:
            match = pattern.match(fname)
            if not match:
                logger.warning(f"Skipping file check {fname} (pattern mismatch)")
                continue
                
            start_days = int(match.group(1))
            end_days = int(match.group(2))
            
            fp = os.path.join(chunks_dir, fname)
            
            # Estimate query dates
            # We assume the file modification time is roughly when the query was run "today"
            # Or just use date.today() if running now. 
            # Using file mtime is safer for historical chunks.
            mtime = os.path.getmtime(fp)
            file_date = date.fromtimestamp(mtime)
            
            q_start_date = file_date - timedelta(days=start_days)
            q_end_date = file_date - timedelta(days=end_days)
            
            try:
                with open(fp, 'r', encoding='utf-8') as f_in:
                    reader = csv.reader(f_in)
                    chunk_header = next(reader, None)
                    if not chunk_header: continue
                    
                    # Check if chunks have different header? Assume same.
                    # Original Header: arxiv_id, title, abstract, authors, primary_category, all_categories, published_at, citation_count
                    
                    for row in reader:
                        # row layout is preserved
                        aid = row[0]
                        if aid not in seen_ids:
                            # Append metadata
                            new_row = row + [
                                start_days, end_days, 
                                q_start_date.isoformat(), 
                                q_end_date.isoformat()
                            ]
                            writer.writerow(new_row)
                            seen_ids.add(aid)
                            rows_written += 1
                            
            except Exception as e:
                logger.error(f"Error processing {fname}: {e}")

    logger.info(f"Done. Wrote {rows_written} entries.")

if __name__ == "__main__":
    merge_chunks()
