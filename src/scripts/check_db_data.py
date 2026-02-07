from src.database import get_db
from src.models.run import Run
from src.models.paper import Paper
from sqlalchemy import select, func

def check_data():
    db = next(get_db())
    try:
        # Check Runs
        print("--- Runs ---")
        runs = db.scalars(select(Run).order_by(Run.id.desc()).limit(5)).all()
        for run in runs:
            print(f"Run ID: {run.id}, Status: {run.status}, Papers Count: {run.papers_count}, Created: {run.created_at}")

        # Check Papers count
        total_papers = db.scalar(select(func.count(Paper.id)))
        print(f"\nTotal Papers in DB: {total_papers}")
        
        # Check Scores
        print("\n--- Paper Scores ---")
        from src.models.score import PaperScore
        scores = db.scalars(select(PaperScore).order_by(PaperScore.final_score.desc()).limit(5)).all()
        if scores:
            for score in scores:
                print(f"Paper ID: {score.paper_id}, Final: {score.final_score:.2f} (Auth: {score.author_score:.2f}, Cat: {score.category_score:.2f}, L: {score.llm_interest_score:.2f})")
        else:
            print("No scores found.")

        # Check Test Paper Score specifically
        print("\n--- Test Paper Score ---")
        test_paper = db.scalar(select(Paper).where(Paper.arxiv_id == "9999.99999"))
        if test_paper and test_paper.score:
             s = test_paper.score
             print(f"ID: {test_paper.id}, Title: {test_paper.title}")
             print(f"Final: {s.final_score:.2f} (Auth: {s.author_score:.2f}, Cat: {s.category_score:.2f}, L: {s.llm_interest_score:.2f})")

        # Check latest paper details
        print("\n--- Latest Paper Sample ---")
        latest_paper = db.scalar(select(Paper).order_by(Paper.id.desc()).limit(1))
        if latest_paper:
            print(f"ID: {latest_paper.id}")
            print(f"ArXiv ID: {latest_paper.arxiv_id}")
            print(f"Title: {latest_paper.title}")
            print(f"Authors: {latest_paper.authors}")
            print(f"Categories: {latest_paper.categories}")
            print(f"Published: {latest_paper.published_at}")
            print(f"Abstract preview: {latest_paper.abstract[:200]}...")
            print(f"Raw Abstract length: {len(latest_paper.abstract)}")
        else:
            print("No papers found.")

    finally:
        db.close()

if __name__ == "__main__":
    check_data()
