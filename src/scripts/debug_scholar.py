from semanticscholar import SemanticScholar
import logging

logging.basicConfig(level=logging.INFO)

def test():
    sch = SemanticScholar()
    ids = [
        "ARXIV:1706.03762", # Known paper (Attention is All You Need)
        "1706.03762",
        "ArXiv:1706.03762",
        "arXiv:1706.03762"
    ]
    
    print("Testing ID formats...")
    try:
        results = sch.get_papers(ids, fields=['title', 'citationCount'])
        for res in results:
            print(f"Found: {res.title} (Citations: {res.citationCount}) - ID: {res.paperId}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test()
