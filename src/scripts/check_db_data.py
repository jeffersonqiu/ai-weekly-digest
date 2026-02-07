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
