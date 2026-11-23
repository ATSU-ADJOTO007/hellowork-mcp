from __future__ import annotations

import csv

import pytest

from hellowork_mcp.exports import HISTORY_COLUMNS, export_csv, export_markdown
from hellowork_mcp.redirects import RedirectRegistry, classify_url, is_safe_external_url, normalize_url


@pytest.mark.parametrize(
    ("url", "category"),
    [
        ("https://acme.wd3.myworkdayjobs.com/fr-FR/careers/job/123", "ats"),
        ("https://boards.greenhouse.io/acme/jobs/1", "ats"),
        ("https://jobs.lever.co/acme/abc", "ats"),
        ("https://acme.teamtailor.com/jobs/42", "ats"),
        ("https://fr.indeed.com/viewjob?jk=1", "job_board"),
        ("https://www.welcometothejungle.com/fr/companies/acme/jobs/x", "job_board"),
        ("https://www.linkedin.com/jobs/view/1", "job_board"),
        ("https://careers.acme.com/offre/1", "company_careers"),
        ("https://www.acme.fr/recrutement/offre-1", "company_careers"),
        ("https://www.acme.fr/produits", "other"),
        ("not a url", "other"),
    ],
)
def test_classify_url(url, category):
    assert classify_url(url) == category


def test_normalize_and_safety():
    assert normalize_url("HTTPS://Jobs.Lever.co/acme/1/?utm_source=hw&ref=2#apply") == "https://jobs.lever.co/acme/1?ref=2"
    assert is_safe_external_url("https://example.com/a")
    assert not is_safe_external_url("javascript:alert(1)")
    assert not is_safe_external_url("file:///etc/passwd")


def test_registry_deduplicates_and_marks_opened():
    registry = RedirectRegistry()
    common = dict(offer_id="1", title="Poste", company="Exemple", hellowork_url="https://www.hellowork.com/fr-fr/emplois/1.html")
    entry, created = registry.record(external_url="https://jobs.lever.co/acme/1?utm_source=hw", **common)
    assert created and entry["category"] == "ats" and entry["opened_in_browser"] is False
    again, created_again = registry.record(external_url="https://jobs.lever.co/acme/1/", **common)
    assert not created_again and again["key"] == entry["key"]
    assert len(registry.all()) == 1
    opened = registry.mark_opened("https://jobs.lever.co/acme/1")
    assert opened["opened_in_browser"] is True and opened["opened_at"]
    with pytest.raises(ValueError):
        registry.record(external_url="javascript:alert(1)", **common)


ROWS = [
    {"offer_id": "1", "title": "Développeur | Python", "company": "Exemple", "status_label": "offre retenue", "score": 80},
    {"offer_id": "2", "title": "=HYPERLINK(\"http://x\")", "company": "Société; Fictive", "status_label": "offre rejetée", "score": None},
]


def test_export_csv_excel_compatible(tmp_path):
    path = export_csv(ROWS, HISTORY_COLUMNS, "test offres", directory=tmp_path)
    assert path.name.startswith("test-offres-") and path.suffix == ".csv"
    raw = path.read_bytes()
    assert raw.startswith(b"\xef\xbb\xbf")  # BOM UTF-8 pour Excel
    with path.open(encoding="utf-8-sig", newline="") as fh:
        rows = list(csv.reader(fh, delimiter=";"))
    assert rows[0] == HISTORY_COLUMNS
    assert rows[1][1] == "Développeur | Python"
    assert rows[2][1].startswith("'=")  # injection de formule neutralisée
    assert rows[2][2] == "Société; Fictive"


def test_export_markdown(tmp_path):
    path = export_markdown(ROWS, HISTORY_COLUMNS, "offres", "Offres", directory=tmp_path)
    text = path.read_text(encoding="utf-8")
    assert text.startswith("# Offres")
    assert "Développeur \\| Python" in text
    assert "2 ligne(s)" in text


def test_exports_are_unique(tmp_path):
    first = export_csv(ROWS, HISTORY_COLUMNS, "x", directory=tmp_path)
    second = export_csv(ROWS, HISTORY_COLUMNS, "x", directory=tmp_path)
    assert first != second
