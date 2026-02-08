# Phase 12: Citation-Based Prediction Scoring (Subsequent to Phase 11 MVP)

> **Goal**: Replace heuristic scoring (authors/categories) with a machine learning model that predicts a paper's future impact (citations) based on its metadata, blended 50/50 with LLM interest assessment.

## 1. Overview & Strategy

We are moving from "Rule-Based Ranking" to "AI-Based Ranking".
Instead of hardcoding specific authors, we will train a model on historical data to learn what high-impact papers look like.

### The New Scoring Formula
```python
Final_Score = (0.5 * Predicted_Impact_Score) + (0.5 * LLM_Interest_Score)
```
*   **Predicted_Impact_Score**: Model's prediction of future citations (normalized to 0-1).
*   **LLM_Interest_Score**: GPT-4o-mini's assessment of novelty/relevance.
*   **Removed**: Explicit `author_score` and `category_score`.
*   **Retained**: Category *filtering* (we only download papers in target domains).

### Data Source
**Semantic Scholar API** (Graph API)
-   Used to get ground-truth citation counts for training labels.

### Training Strategy
-   **Frequency**: Monthly (via GitHub Actions or manual).
-   **Training Data**: Papers published > 2 months ago (configurable based on EDA) to ensure citation signal is present.
-   **Inference**: Applied to ALL papers (including new ones). The model predicts "expected impact".

---

## 2. Implementation Steps

### Step 1: Exploratory Data Analysis (EDA)
**Goal**: Determine the ideal "age" threshold for training papers.
*Current hypothesis: >1-2 months.*

-   [ ] Create `notebooks/eda_citation_growth.ipynb`
-   [ ] Fetch metadata/citations for papers at varying ages (1-6 months).
-   [ ] Analyze correlation between early citations and long-term impact.
-   [ ] Define `MIN_PAPER_AGE_DAYS` for valid training samples.

### Step 2: Semantic Scholar Client
**Goal**: Service to fetch citation counts.

-   [ ] Create `src/services/scholar/client.py`.
-   [ ] Implement `get_citations(arxiv_ids)` using Semantic Scholar Graph API.
-   [ ] Handle rate limits.

### Step 3: Dataset Creation Pipeline
**Goal**: specific script to build `training_data.csv`.

-   [ ] Create `src/scripts/build_training_data.py`.
-   [ ] Fetch papers matching `MIN_PAPER_AGE_DAYS`.
-   [ ] Query Semantic Scholar for citation counts.
-   [ ] Save to CSV (Features: Title, Abstract, Authors, Categories; Target: Citations).

### Step 4: Model Training Pipeline
**Goal**: Train XGBoost/LightGBM regressor.

-   [ ] Add dependencies: `scikit-learn`, `xgboost`, `openai` (for embeddings).
-   [ ] Create `src/services/prediction/trainer.py`.
    -   **Features**: OpenAI Embeddings (Title+Abstract), Author historical stats (if available), One-hot Categories.
    -   **Model**: XGBoost Regressor.
    -   **Output**: Serialized model artifact.

### Step 5: Integration & Scorer Update
**Goal**: Use model for ranking.

-   [ ] Create `src/services/prediction/inference.py` (Load model, predict).
-   [ ] Update `src/services/ranking/scorer.py`:
    -   Remove `calculate_author_score` and `calculate_category_score`.
    -   Add `PredictionService`.
    -   Implement 50/50 blend logic.

---

## 3. Directory Structure Updates

```
src/
├── services/
│   ├── scholar/         # New: Semantic Scholar integration
│   ├── prediction/      # New: Training & Inference logic
│   └── ranking/
│       └── scorer.py    # Modified
notebooks/
└── eda_citation_growth.ipynb
```
