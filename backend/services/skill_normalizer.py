"""Skill normalization: maps many written forms of the same skill to one
canonical display name (e.g. "Postgres" / "PostgreSQL" -> "PostgreSQL").

This is a fixed dictionary lookup, not fuzzy string merging — two skills
are only treated as the same skill when they're literally the same
normalized text or explicitly listed as aliases of each other here.
Looking similar is not enough (e.g. "Java" and "JavaScript" must never
merge). Original wording is always preserved for display; only the
canonical name is used internally for matching/deduplication.
"""

import re

# alias (any case/spacing) -> canonical display name.
# Keys are matched after _clean() normalization (lowercase, punctuation
# stripped, whitespace collapsed), so "Node.js", "nodejs", "node js" all
# reach the same lookup key.
SKILL_ALIASES: dict[str, str] = {
    # Languages
    "python": "Python",
    "py": "Python",
    "javascript": "JavaScript",
    "js": "JavaScript",
    "typescript": "TypeScript",
    "ts": "TypeScript",
    "java": "Java",
    "c++": "C++",
    "cpp": "C++",
    "c#": "C#",
    "csharp": "C#",
    "golang": "Go",
    "go": "Go",
    # Web / API
    "rest api": "REST API",
    "rest apis": "REST API",
    "restful api": "REST API",
    "restful apis": "REST API",
    "graphql": "GraphQL",
    "nodejs": "Node.js",
    "node js": "Node.js",
    "nodejs js": "Node.js",
    "reactjs": "React",
    "react js": "React",
    "react": "React",
    "vuejs": "Vue.js",
    "vue js": "Vue.js",
    "angularjs": "Angular",
    "angular": "Angular",
    "fastapi": "FastAPI",
    "flask": "Flask",
    "django": "Django",
    "express": "Express.js",
    "expressjs": "Express.js",
    # Databases
    "sql": "SQL",
    "postgres": "PostgreSQL",
    "postgresql": "PostgreSQL",
    "mysql": "MySQL",
    "mongodb": "MongoDB",
    "mongo": "MongoDB",
    "nosql": "NoSQL",
    "sqlite": "SQLite",
    "redis": "Redis",
    # Cloud / DevOps
    "aws": "AWS",
    "amazon web services": "AWS",
    "gcp": "Google Cloud Platform",
    "google cloud": "Google Cloud Platform",
    "google cloud platform": "Google Cloud Platform",
    "azure": "Microsoft Azure",
    "microsoft azure": "Microsoft Azure",
    "docker": "Docker",
    "kubernetes": "Kubernetes",
    "k8s": "Kubernetes",
    "ci cd": "CI/CD",
    "cicd": "CI/CD",
    "ci/cd": "CI/CD",
    "terraform": "Terraform",
    "linux": "Linux",
    "git": "Git",
    "github": "Git",
    "github actions": "GitHub Actions",
    # Data / ML
    "machine learning": "Machine Learning",
    "ml": "Machine Learning",
    "deep learning": "Deep Learning",
    "dl": "Deep Learning",
    "natural language processing": "Natural Language Processing",
    "nlp": "Natural Language Processing",
    "computer vision": "Computer Vision",
    "cv": "Computer Vision",
    "pandas": "Pandas",
    "numpy": "NumPy",
    "scikit learn": "scikit-learn",
    "sklearn": "scikit-learn",
    "tensorflow": "TensorFlow",
    "pytorch": "PyTorch",
    "data analysis": "Data Analysis",
    "data analytics": "Data Analysis",
    # Testing / other tooling
    "pytest": "pytest",
    "unit testing": "Unit Testing",
    "agile": "Agile",
    "scrum": "Scrum",
    "microservices": "Microservices",
    "object oriented programming": "Object-Oriented Programming",
    "oop": "Object-Oriented Programming",
}

_WHITESPACE_RE = re.compile(r"\s+")
_PUNCT_RE = re.compile(r"[^\w\s+#./]")


def _clean(raw: str) -> str:
    """Lowercase, strip most punctuation (but keep +, #, ., / which are
    meaningful in skill names like C++, C#, Node.js, CI/CD), collapse
    whitespace."""
    text = raw.strip().lower()
    text = _PUNCT_RE.sub(" ", text)
    text = _WHITESPACE_RE.sub(" ", text).strip()
    return text


def normalize_skill(raw: str) -> str:
    """Returns the canonical display name for a skill string. Falls back
    to a cleaned, title-cased version of the original text when there is
    no known alias — unknown skills still get a stable, consistent
    display form, they just aren't merged with anything else."""
    if not raw or not raw.strip():
        return raw

    cleaned = _clean(raw)
    if cleaned in SKILL_ALIASES:
        return SKILL_ALIASES[cleaned]

    # Preserve common all-caps/mixed-case acronyms as-is (e.g. "SQL", "AWS")
    # rather than title-casing them into "Sql"/"Aws".
    stripped = raw.strip()
    if stripped.isupper() and len(stripped) <= 6:
        return stripped

    return " ".join(word if word.isupper() else word.capitalize() for word in stripped.split())


def skills_match(a: str, b: str) -> bool:
    """True when two skill strings normalize to the same canonical skill."""
    return normalize_skill(a) == normalize_skill(b)
