from services.skill_normalizer import normalize_skill, skills_match


def test_known_aliases_normalize_to_canonical_name():
    assert normalize_skill("Postgres") == "PostgreSQL"
    assert normalize_skill("postgresql") == "PostgreSQL"
    assert normalize_skill("PostgreSQL") == "PostgreSQL"

    assert normalize_skill("REST APIs") == "REST API"
    assert normalize_skill("rest api") == "REST API"
    assert normalize_skill("RESTful API") == "REST API"

    assert normalize_skill("Machine Learning") == "Machine Learning"
    assert normalize_skill("ML") == "Machine Learning"
    assert normalize_skill("ml") == "Machine Learning"


def test_skills_match_uses_canonical_equivalence():
    assert skills_match("Postgres", "PostgreSQL") is True
    assert skills_match("ML", "Machine Learning") is True
    assert skills_match("Python", "Java") is False


def test_unrelated_similar_looking_skills_never_merge():
    # These must never be treated as the same skill just because they share
    # letters/prefixes.
    assert normalize_skill("Java") != normalize_skill("JavaScript")
    assert skills_match("Java", "JavaScript") is False


def test_unknown_skill_gets_stable_cleaned_display_form():
    result = normalize_skill("some totally unknown skill")
    assert result == "Some Totally Unknown Skill"
    # Calling it again must be stable/deterministic.
    assert normalize_skill("some totally unknown skill") == result


def test_short_all_caps_acronym_preserved():
    assert normalize_skill("AWS") == "AWS"
    assert normalize_skill("SQL") == "SQL"


def test_punctuation_variants_normalize_the_same():
    assert normalize_skill("Node.js") == normalize_skill("nodejs") == normalize_skill("node js")
    assert normalize_skill("CI/CD") == normalize_skill("ci cd") == normalize_skill("CICD")
