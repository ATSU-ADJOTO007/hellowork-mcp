from __future__ import annotations

import json

import pytest

from hellowork_mcp.config import Config, ConfigError, config_path, load_config, save_config, update_config


def test_defaults_when_missing():
    config = load_config()
    assert config.dry_run is True
    assert config.max_applications_per_day == 10
    assert config.thresholds.relevant == 70


def test_save_and_reload():
    save_config(Config(job_titles=["Développeur Python"], locations=["Lyon"], min_salary=42000))
    reloaded = load_config()
    assert reloaded.job_titles == ["Développeur Python"]
    assert reloaded.min_salary == 42000
    assert json.loads(config_path().read_text(encoding="utf-8"))["locations"] == ["Lyon"]


def test_update_partial_and_thresholds():
    update_config({"job_titles": ["Data engineer", " data   engineer ", "DevOps"]})
    config = update_config({"thresholds": {"review": 40}})
    assert config.job_titles == ["Data engineer", "DevOps"]  # doublons et espaces nettoyés
    assert config.thresholds.review == 40 and config.thresholds.relevant == 70


@pytest.mark.parametrize(
    "changes",
    [
        {"unknown_field": 1},
        {"min_score": 150},
        {"max_applications_per_day": -1},
        {"remote_preference": "souvent"},
        {"thresholds": {"review": 90, "relevant": 60}},
        {"request_delay_seconds": 0},
    ],
)
def test_update_rejects_invalid(changes):
    with pytest.raises(ConfigError):
        update_config(changes)
    assert load_config() == Config()  # rien n'a été écrit


def test_invalid_file_reports_error():
    config_path().write_text(json.dumps({"min_score": "beaucoup"}), encoding="utf-8")
    with pytest.raises(ConfigError):
        load_config()
