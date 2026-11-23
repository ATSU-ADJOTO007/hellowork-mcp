from __future__ import annotations

from hellowork_mcp.config import Config, Thresholds
from hellowork_mcp.filters import contains_keyword, match_keywords, normalize, strip_html
from hellowork_mcp.models import Offer, Salary
from hellowork_mcp.scoring import score_offer


def make_offer(**overrides) -> Offer:
    data = dict(
        offer_id="10000001",
        url="https://www.hellowork.com/fr-fr/emplois/10000001.html",
        title="Développeur Python Senior H/F",
        company="Exemple Data",
        location="Lyon",
        region="Auvergne-Rhône-Alpes",
        postal_code="69000",
        contract="CDI",
        remote="partial",
        salary=Salary(min=45000, max=55000, period="YEAR"),
        description="API avec Python, Django et PostgreSQL. Déploiement Docker.",
        skills=["Python", "Django"],
        direct_apply=True,
    )
    data.update(overrides)
    return Offer(**data)


def test_normalize_and_keywords():
    assert normalize("  Développeur   ÉLECTRONIQUE ") == "developpeur electronique"
    assert contains_keyword("Expérience Java requise", "java")
    assert not contains_keyword("JavaScript et TypeScript", "java")
    assert contains_keyword("Poste de développeur C++", "c++")
    assert match_keywords("python django", ["Python", "Go"]) == (["Python"], ["Go"])
    assert strip_html("<p>Un&nbsp;deux<br/>trois</p>") == "Un deux\ntrois"


def test_perfect_match_is_relevant():
    config = Config(
        job_titles=["Développeur Python"],
        required_keywords=["Django", "PostgreSQL"],
        contract_types=["CDI"],
        locations=["Lyon"],
        min_salary=40000,
        remote_preference="hybrid",
    )
    result = score_offer(make_offer(), config)
    assert result.score == 100
    assert result.decision == "relevant"
    assert result.missing == []
    assert sum(result.breakdown.values()) == 100


def test_unconfigured_criteria_give_full_points():
    result = score_offer(make_offer(), Config())
    assert result.score == 100


def test_missing_information_gives_half_points_and_warnings():
    config = Config(contract_types=["CDI"], locations=["Lyon"], min_salary=40000, remote_preference="remote")
    offer = make_offer(contract=None, location=None, region=None, postal_code=None, salary=None, remote=None)
    result = score_offer(offer, config)
    assert result.breakdown["contract"] == 7.5
    assert result.breakdown["salary"] == 5
    assert "Salaire non communiqué" in result.warnings
    assert "Localisation non précisée" in result.warnings


def test_mismatches_lower_the_score():
    config = Config(
        job_titles=["Comptable"],
        required_keywords=["SAP", "Python"],
        contract_types=["CDD"],
        locations=["Paris"],
        min_salary=60000,
        thresholds=Thresholds(relevant=70, review=50),
    )
    result = score_offer(make_offer(), config)
    assert result.breakdown["title"] == 0
    assert result.breakdown["keywords"] == 12.5
    assert result.breakdown["contract"] == 0
    assert result.breakdown["location"] == 0
    assert result.breakdown["salary"] == 0
    assert result.decision == "not_relevant"


def test_partial_title_match_and_review_decision():
    config = Config(job_titles=["Développeur Java Senior"], contract_types=["CDI"], thresholds=Thresholds(relevant=95, review=50))
    result = score_offer(make_offer(), config)
    assert 0 < result.breakdown["title"] < 25
    assert result.decision == "review"


def test_excluded_keyword_forces_zero():
    result = score_offer(make_offer(), Config(excluded_keywords=["docker"]))
    assert result.score == 0
    assert result.decision == "not_relevant"
    assert result.excluded_keywords_found == ["docker"]


def test_already_processed_and_postal_code_location():
    config = Config(locations=["69"])
    result = score_offer(make_offer(), config, already_processed=True)
    assert result.breakdown["location"] == 15
    assert result.decision == "already_processed"


def test_full_remote_satisfies_any_location():
    result = score_offer(make_offer(location="Nantes", region=None, postal_code="44000", remote="full"), Config(locations=["Lyon"]))
    assert result.breakdown["location"] == 15


def test_external_offer_warning():
    result = score_offer(make_offer(direct_apply=False, external_apply_url="https://jobs.lever.co/x/1"), Config())
    assert "Candidature sur un site externe" in result.warnings


def test_monthly_salary_is_annualized():
    offer = make_offer(salary=Salary(min=3000, period="MONTH"))
    assert offer.salary.annual_min() == 36000
    assert score_offer(offer, Config(min_salary=40000)).breakdown["salary"] == 0
