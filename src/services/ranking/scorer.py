"""Scoring service for arXiv papers.

Handles heuristic scoring signals:
- Recency: Newer papers get higher scores.
- Category: Papers in priority categories get higher scores.
- Final Score: Weighted combination of signals.
"""

from datetime import datetime, timezone, timedelta

from src.config import get_settings
from src.models.paper import Paper
from src.models.score import PaperScore


class PaperScorer:
    """Calculates scoring signals for papers."""

    def __init__(self):
        self.settings = get_settings()

    def calculate_author_score(self, authors: list[str]) -> float:
        """Calculate author score (0.0 to 1.0).
        
        Strategy:
        - 1.0 if any author is in our priority list.
        - 0.0 otherwise.
        """
        priority_authors = self.settings.priority_author_list
        if not priority_authors:
            return 0.0
            
        for author in authors:
            # Check for partial match (e.g. "Geoffrey Hinton" matches "hinton")
            author_lower = author.lower()
            for priority in priority_authors:
                if priority in author_lower:
                    return 1.0
                    
        return 0.0

    def calculate_category_score(self, paper_categories: str) -> float:
        """Calculate category score (0.0 to 1.0).
        
        Strategy:
        - 1.0 if the PRIMARY category is in our target list.
        - 0.5 if a secondary category is in our target list.
        - 0.1 otherwise.
        """
        target_categories = self.settings.arxiv_category_list
        paper_cats = [c.strip() for c in paper_categories.split(",")]
        
        if not paper_cats:
            return 0.0
            
        primary_cat = paper_cats[0]
        
        if primary_cat in target_categories:
            return 1.0
            
        # Check if any other category matches
        for cat in paper_cats[1:]:
            if cat in target_categories:
                return 0.5
                
        return 0.1

    def calculate_heuristic_score(self, paper: Paper) -> tuple[float, float]:
        """Calculate heuristic scores (author, category) for a paper.
        
        Returns:
            tuple[float, float]: (author_score, category_score)
        """
        author = self.calculate_author_score(paper.authors)
        category = self.calculate_category_score(paper.categories)
        return author, category

    def calculate_final_score(
        self, 
        author_score: float, 
        category_score: float, 
        llm_score: float
    ) -> float:
        """Calculate final composite score.
        
        Weights:
        - Author: 0.10 (User requested)
        - Category: 0.40
        - LLM Interest: 0.50
        """
        return (
            0.10 * author_score +
            0.40 * category_score +
            0.50 * llm_score
        )
