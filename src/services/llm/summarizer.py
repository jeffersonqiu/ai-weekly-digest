"""Summarizer service for generating digest."""

import json
import logging
from typing import List, Dict, Any

from src.models.paper import Paper
from src.services.llm.client import LLMClient
from src.services.llm.prompts import (
    PAPER_SUMMARY_SYSTEM_PROMPT,
    PAPER_SUMMARY_PROMPT,
    DIGEST_COMPILATION_SYSTEM_PROMPT,
    DIGEST_COMPILATION_PROMPT,
)

logger = logging.getLogger(__name__)

class DigestSummarizer:
    """Service to summarize papers and generate the digest."""
    
    def __init__(self):
        self.llm = LLMClient()
        
    def summarize_paper(self, paper: Paper) -> Dict[str, Any]:
        """Generate a structured summary for a single paper."""
        try:
            prompt = PAPER_SUMMARY_PROMPT.format(
                title=paper.title,
                abstract=paper.abstract
            )
            
            summary = self.llm.get_structured_completion(
                prompt=prompt,
                system_prompt=PAPER_SUMMARY_SYSTEM_PROMPT
            )
            
            # Enrich with metadata
            summary["arxiv_id"] = paper.arxiv_id
            summary["title"] = paper.title
            summary["link"] = f"https://arxiv.org/abs/{paper.arxiv_id}"
            
            return summary
            
        except Exception as e:
            logger.error(f"Failed to summarize paper {paper.arxiv_id}: {e}")
            return {
                "arxiv_id": paper.arxiv_id,
                "title": paper.title,
                "error": str(e)
            }
            
    def generate_digest_markdown(self, summaries: List[Dict[str, Any]]) -> str:
        """Compile a markdown digest from a list of paper summaries."""
        try:
            # Prepare JSON for the LLM context
            papers_json = json.dumps(summaries, indent=2)
            
            prompt = DIGEST_COMPILATION_PROMPT.format(
                papers_json=papers_json,
                link="{link}" # Keep literal for f-string in prompt if needed, but here we passed data in json
            )
            
            # Fix: The prompt expects {link} to be used in the generated text, 
            # but we are formatting the prompt string itself. 
            # Actually, the prompt in prompts.py has {link} as a placeholder in the instruction example.
            # We should double check if prompts.py uses {link} as a format placeholder or literal.
            # In prompts.py: "### [Title]({link})" -> It is inside the instruction string.
            # Python f-string will try to replace it. We need to escape it or handle it.
            # Let's adjust the prompt in prompts.py or use safe formatting.
            # For now, let's assume valid json passed contains the links.
            
            digest = self.llm.get_completion(
                prompt=prompt,
                system_prompt=DIGEST_COMPILATION_SYSTEM_PROMPT
            )
            
            return digest
            
        except Exception as e:
            logger.error(f"Failed to generate digest: {e}")
            return "Failed to generate digest."
