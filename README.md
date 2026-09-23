# AI Resume & Career Intelligence Platform

An evidence-grounded resume/job-description analysis platform for two audiences:

- **Job Seekers** — upload a resume + a job description and get a job-fit score,
  matched/missing skills with evidence, a learning roadmap, and a mock interview
  with AI feedback — plus multi-role career intelligence, resume quality checks,
  an ATS/recruiter preview, and external evidence checks (GitHub, LinkedIn).
- **Job Providers / Recruiters** — set a job description once, then upload and
  compare multiple candidate resumes against it using the exact same analysis
  engine.

Every score and claim is grounded in real extracted text, not invented. When AI
is unavailable (no key, `DEMO_MODE`, or a provider failure), every feature
degrades to an honest, clearly-labeled deterministic fallback instead of
guessing — the app never fabricates a fact about a candidate.

## Stack

- **Backend**: FastAPI + SQLAlchemy + SQLite, PyMuPDF/python-docx for parsing,
  Sentence Transformers for local semantic matching, and the Anthropic SDK
  (Claude) for AI-assisted extraction/generation.
- **Frontend**: React + Vite (JavaScript), axios, recharts, lucide-react.

## Setup

### Backend

```bash
cd backend
python3 -m venv venv
source venv/bin/activate        # fish shell: source venv/bin/activate.fish
pip install -r requirements.txt
cp .env.example .env
```

Edit `backend/.env` and fill in `ANTHROPIC_API_KEY` (get one at
https://console.anthropic.com/settings/keys) to enable live AI features.
Leaving it blank, or setting `DEMO_MODE=true`, runs the app fully in its
deterministic fallback mode — useful for development without a key.

```bash
uvicorn main:app --reload
```

The API serves at `http://localhost:8000`; `/health` reports whether AI is
configured.

### Frontend

```bash
cd frontend
npm install
cp .env.example .env   # only needed if the backend isn't on localhost:8000
npm run dev
```

Open `http://localhost:5173`.

### Tests

```bash
cd backend
source venv/bin/activate
pytest
```

The test suite never makes live AI or network calls — every AI/network
dependency is mocked so tests are deterministic and free to run.

## Feature map

| Area | What it does |
|---|---|
| Resume/JD parsing | PDF, DOCX, TXT resumes; TXT/pasted-text job descriptions only |
| AI structured analysis | Extracts skills/experience/education with quoted evidence, never invented |
| Skill matching & scoring | Exact/literal/semantic evidence matching, priority-weighted job-fit score |
| Learning roadmap & interview prep | Per-gap roadmap with a real YouTube search link; mock interview questions |
| Interview answer feedback | AI evaluates a typed practice answer and suggests one follow-up question |
| Career intelligence | Radar of fit across common role profiles, plus a career trajectory timeline |
| Resume intelligence | Bullet quality/quantification checks, an AI rewrite workspace with before/after |
| ATS / recruiter view | Raw-parse preview, JD↔resume keyword diff, heuristic 6-second scan |
| External evidence | GitHub profile/language check, manual LinkedIn consistency check, fairness scan |
| Job Provider mode | One job description, many candidates, same engine, side-by-side comparison |

## Notes

- `backend/app.db` (SQLite) and `backend/.env` are gitignored and local-only —
  delete `app.db` any time to reset to a clean database (it's recreated
  automatically on the next backend start).
- Scores are explicitly labeled as an application-generated estimate, not an
  official ATS or hiring decision.
