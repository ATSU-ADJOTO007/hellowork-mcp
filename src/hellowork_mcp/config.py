"""Configuration persistante des critères de recherche et des protections."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, Field, ValidationError, field_validator, model_validator

from .paths import data_dir
from .storage import read_json, write_json

RemotePreference = Literal["any", "remote", "hybrid", "onsite"]
ExternalRedirectMode = Literal["record_only", "open_in_browser", "ignore"]


class Thresholds(BaseModel):
    relevant: int = Field(default=70, ge=0, le=100, description="Score à partir duquel l'offre est pertinente")
    review: int = Field(default=50, ge=0, le=100, description="Score à partir duquel l'offre est à examiner")

    @model_validator(mode="after")
    def _order(self) -> Thresholds:
        if self.review > self.relevant:
            raise ValueError("thresholds.review doit être inférieur ou égal à thresholds.relevant")
        return self


class Config(BaseModel):
    job_titles: list[str] = Field(default_factory=list, description="Postes recherchés")
    required_keywords: list[str] = Field(default_factory=list, description="Mots-clés obligatoires")
    excluded_keywords: list[str] = Field(default_factory=list, description="Mots-clés interdits")
    contract_types: list[str] = Field(default_factory=list, description="Ex. CDI, CDD, Intérim, Stage, Alternance")
    locations: list[str] = Field(default_factory=list, description="Villes, départements ou régions")
    min_salary: int | None = Field(default=None, ge=0, description="Salaire annuel brut minimum en euros")
    remote_preference: RemotePreference = "any"
    min_score: int = Field(default=60, ge=0, le=100, description="Score minimal pour autoriser une candidature")
    thresholds: Thresholds = Field(default_factory=Thresholds)
    max_applications_per_day: int = Field(default=10, ge=0, le=200)
    dry_run: bool = Field(default=True, description="Mode simulation : aucune candidature réelle n'est envoyée")
    external_redirect_mode: ExternalRedirectMode = "record_only"
    request_delay_seconds: float = Field(default=1.5, ge=0.5, le=30, description="Pause entre deux requêtes")
    headless: bool = Field(default=True, description="Navigateur invisible hors connexion manuelle")

    @field_validator("job_titles", "required_keywords", "excluded_keywords", "contract_types", "locations")
    @classmethod
    def _clean_list(cls, values: list[str]) -> list[str]:
        cleaned: list[str] = []
        for value in values:
            item = " ".join(str(value).split())
            if item and item.lower() not in {c.lower() for c in cleaned}:
                cleaned.append(item)
        return cleaned


def config_path() -> Path:
    return data_dir() / "config.json"


def load_config(path: Path | None = None) -> Config:
    raw = read_json(path or config_path(), dict)
    try:
        return Config.model_validate(raw)
    except ValidationError as exc:
        raise ConfigError(f"Configuration invalide dans {path or config_path()} : {exc}") from exc


def save_config(config: Config, path: Path | None = None) -> None:
    write_json(path or config_path(), config.model_dump(mode="json"))


def update_config(changes: dict[str, Any], path: Path | None = None) -> Config:
    """Applique des changements partiels. Les champs inconnus sont refusés."""
    current = load_config(path).model_dump(mode="json")
    unknown = sorted(set(changes) - set(Config.model_fields))
    if unknown:
        raise ConfigError(f"Champs inconnus : {', '.join(unknown)}. Champs valides : {', '.join(Config.model_fields)}")
    for key, value in changes.items():
        if key == "thresholds" and isinstance(value, dict):
            current["thresholds"] = {**current["thresholds"], **value}
        else:
            current[key] = value
    try:
        config = Config.model_validate(current)
    except ValidationError as exc:
        raise ConfigError(str(exc)) from exc
    save_config(config, path)
    return config


class ConfigError(ValueError):
    pass
