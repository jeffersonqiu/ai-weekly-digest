"""Script to generate the weekly digest.

Top 20 papers from the latest run are summarized and compiled into a Markdown digest.
"""

import sys
import os
import logging
from datetime import date
from collections import Counter
import matplotlib.pyplot as plt
import matplotlib.cm as cm
import matplotlib.colors as mcolors
import numpy as np

from sqlalchemy import select
from src.database import get_db
from src.models.run import Run
from src.models.paper import Paper
from src.models.score import PaperScore
from src.models.digest import Digest
from src.services.llm.summarizer import DigestSummarizer

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# Category definitions and icons
CATEGORY_ICONS = {
    "Model Design": "🏗️",
    "Training & Optimization": "🏋️",
    "Evaluation & Metrics": "📏",
    "Agents & Systems": "🤖",
    "Safety & Applications": "🛡️",
    "Miscellaneous": "📦"
}

def classify_paper_heuristic(paper: Paper) -> str:
    """Heuristically classify a paper into one of the categories based on title/abstract."""
    text = (paper.title + " " + paper.abstract).lower()
    
    # Simple keyword matching (priority ordered)
    if any(k in text for k in ["agent", "multi-agent", "robot", "planning", "tool use", "retrieval", "rag"]):
        return "Agents & Systems"
    if any(k in text for k in ["safety", "jailbreak", "bias", "fairness", "detection", "medical", "finance", "application"]):
        return "Safety & Applications"
    if any(k in text for k in ["evaluation", "benchmark", "metric", "survey", "analysis", "dataset"]):
        return "Evaluation & Metrics"
    if any(k in text for k in ["training", "optimization", "finetuning", "fine-tuning", "quantization", "pruning", "efficiency", "gradient"]):
        return "Training & Optimization"
    if any(k in text for k in ["architecture", "transformer", "attention", "diffusion", "mamba", "moe", "model"]):
        return "Model Design"
        
    return "Miscellaneous"

def generate_category_chart(run_id: int, db, output_path: str) -> str:
    """Generate a horizontal bar chart of paper categories with intensity coloring."""
    
    # 1. Fetch ALL papers for this run
    stmt = select(Paper).where(Paper.run_id == run_id)
    all_papers = db.scalars(stmt).all()
    
    # 2. Classify all papers
    categories = [classify_paper_heuristic(p) for p in all_papers]
    total_papers = len(categories)
    counts = Counter(categories)
    
    # 3. Sort by count for better visualization
    valid_categories = list(CATEGORY_ICONS.keys())
    # Filter only present categories
    present_categories = [c for c in valid_categories if counts[c] > 0]
    # Sort by count ascending (for horizontal bar chart to have max at top)
    present_categories.sort(key=lambda c: counts[c], reverse=False)
    
    plot_labels = present_categories
    plot_values = [counts[c] for c in plot_labels]
    
    # 4. Styling & Intensity Coloring
    plt.style.use('seaborn-v0_8-whitegrid')
    fig, ax = plt.subplots(figsize=(10, 6))
    
    # Color map selection (e.g., Blues or Viridis)
    cmap = cm.get_cmap('YlOrRd') # Yellow-Orange-Red 
    norm = mcolors.Normalize(vmin=0, vmax=max(plot_values)*1.2) # Normalize based on max count
    colors = [cmap(norm(v)) for v in plot_values]
    
    bars = ax.barh(plot_labels, plot_values, color=colors, edgecolor='none', alpha=0.9)
    
    # Remove borders
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.spines['left'].set_visible(False)
    ax.spines['bottom'].set_color('#DDDDDD')
    
    # Title and labels
    ax.set_title(f'Paper Distribution by Category (Total: {total_papers})', fontsize=16, fontweight='bold', pad=20, color='#333333')
    ax.set_xlabel('Number of Papers', fontsize=12, labelpad=10)
    ax.tick_params(axis='y', labelsize=11)
    ax.tick_params(axis='x', bottom=False) # Hide x ticks
    
    # Add counts and percentages at the end of bars
    for bar in bars:
        width = bar.get_width()
        pct = (width / total_papers) * 100
        label = f" {int(width)} ({pct:.1f}%)"
        ax.text(width, bar.get_y() + bar.get_height()/2.,
                 label,
                 ha='left', va='center', fontsize=10, fontweight='bold', color='#555555')

    plt.tight_layout()
    plt.savefig(output_path, dpi=150, bbox_inches='tight')
    plt.close()
    
    return output_path

def generate_digest():
    """Generate the weekly digest for the latest run."""
    db_gen = get_db()
    db = next(db_gen)
    
    try:
        # 1. Get the latest run
        logger.info("Finding latest run...")
        stmt = select(Run).order_by(Run.created_at.desc()).limit(1)
        run = db.execute(stmt).scalar_one_or_none()
        
        if not run:
            logger.error("No runs found.")
            return
        
        logger.info(f"Processing Run ID: {run.id} (Status: {run.status})")
        
        # Determine Date Range
        start_date = run.start_date.strftime("%Y-%m-%d")
        end_date = run.end_date.strftime("%Y-%m-%d")
        date_range_str = f"{start_date} to {end_date}"
        file_base_name = f"digest_{start_date}_to_{end_date}"
        
        # Setup Output Directory
        output_dir = "output/digests"
        os.makedirs(output_dir, exist_ok=True)
        
        # 2. Get top 20 ranked papers
        stmt = (
            select(PaperScore)
            .where(PaperScore.run_id == run.id)
            .where(PaperScore.rank != None)
            .order_by(PaperScore.rank.asc())
            .limit(20)
        )
        scores = db.execute(stmt).scalars().all()
        
        if not scores:
            logger.error(f"No ranked papers found for Run {run.id}. Did you run rank_papers.py?")
            return
            
        logger.info(f"Found {len(scores)} ranked papers. Starting summarization...")
        
        summarizer = DigestSummarizer()
        paper_summaries = []
        
        # 3. Summarize each paper
        for i, score in enumerate(scores, 1):
            paper = score.paper
            logger.info(f"[{i}/{len(scores)}] Summarizing: {paper.title[:50]}...")
            summary = summarizer.summarize_paper(paper)
            
            # Inject Icon into Summary
            cat = summary.get("category", "Miscellaneous")
            # Fallback/Normalization for category from LLM
            # (LLM might return slightly different strings, so we normalize)
            normalized_cat = "Miscellaneous"
            for k in CATEGORY_ICONS.keys():
                if k.lower() in cat.lower():
                    normalized_cat = k
                    break
            
            icon = CATEGORY_ICONS.get(normalized_cat, "📦")
            
            # Add fields for LLM Prompt to use
            summary["category_name"] = normalized_cat
            summary["category_icon"] = icon
            summary["icon"] = icon # Backward compat if needed
            
            paper_summaries.append(summary)
            
        # 4. Generate Chart (Full Set)
        logger.info("Generating full-set category chart...")
        chart_filename = f"{file_base_name}_chart.png"
        chart_path = os.path.join(output_dir, chart_filename)
        generate_category_chart(run.id, db, chart_path)
        
        # 5. Generate Base Digest Content
        logger.info("Compiling digest content...")
        
        # Prepend icon to title ensures it appears in "Worth Skimming" lists if LLM formats that way
        for p in paper_summaries:
             p["title"] = f"{p['icon']} {p['title']}"

        digest_content = summarizer.generate_digest_markdown(paper_summaries)
        
        # 6. Assemble Final Digest
        digest_content = digest_content.replace("# Weekly AI Papers Digest", "").strip()
        
        # Use relative path for image in markdown if they are in same folder
        # But commonly we check where it is opened. Let's assume relative to markdown file.
        # Since markdown is in output/digests, and image is there too, just filename works.
        
        final_digest = f"""# Weekly AI Papers Digest
> **Date Range**: {date_range_str}

**📅 Papers Published This Week:** {run.papers_count or 'N/A'}

## 📊 Category Distribution
![Papers by Category]({chart_filename})

{digest_content}
"""
        
        # 7. Save to DB
        logger.info("Saving digest to database...")
        
        existing_digest = db.execute(select(Digest).where(Digest.run_id == run.id)).scalar_one_or_none()
        if existing_digest:
            logger.info(f"Deleting existing digest for Run {run.id}...")
            db.delete(existing_digest)
            db.commit()
            
        digest_obj = Digest(
            run_id=run.id,
            markdown=final_digest,
            html=None 
        )
        db.add(digest_obj)
        db.commit()
        
        # 8. Save to local file
        output_file_md = os.path.join(output_dir, f"{file_base_name}.md")
        with open(output_file_md, "w") as f:
            f.write(final_digest)
            
        logger.info(f"Digest generated successfully!\n Saved to:\n  - {output_file_md}\n  - {chart_path}")
        
    except Exception as e:
        logger.error(f"Digest generation failed: {e}", exc_info=True)
        db.rollback()
        sys.exit(1)
    finally:
        db.close()

if __name__ == "__main__":
    generate_digest()
