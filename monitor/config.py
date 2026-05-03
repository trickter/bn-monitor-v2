from __future__ import annotations

import json
from decimal import Decimal, InvalidOperation
from enum import StrEnum
from typing import Any

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class AlertMode(StrEnum):
    SHADOW = "shadow"
    LIVE = "live"


class Severity(StrEnum):
    INFO = "INFO"
    WARNING = "WARNING"
    CRITICAL = "CRITICAL"


class UniverseMode(StrEnum):
    TOP_USDT = "top_usdt"
    EXPLICIT = "explicit"


KNOWN_RULE_THRESHOLDS: dict[str, frozenset[str]] = {
    "flat_oi_buildup_15m": frozenset({"return_limit", "oi_buildup_threshold"}),
    "daily_flat_oi_buildup": frozenset({"return_limit", "oi_buildup_threshold"}),
    "breakout_watch": frozenset({"near_high_bps", "range_compression_max", "volume_z_min", "taker_buy_min", "market_return_min"}),
    "breakdown_watch": frozenset({"low_distance_bps", "range_compression_max", "volume_z_min", "taker_sell_min"}),
}

KNOWN_ALERT_TYPES = frozenset(
    {
        "price_probe",
        "volume_expansion_5m",
        "active_buy_impulse",
        "active_sell_impulse",
        "wick_hunt",
        "liquidation_spike_5m",
        "flat_oi_buildup_15m",
        "daily_flat_oi_buildup",
        "breakout_watch",
        "breakdown_watch",
        "long_squeeze_risk",
        "short_squeeze_risk",
        "market_digest",
        "symbol_alert_bundle",
    }
)

SEVERITY_RANK = {
    Severity.INFO: 1,
    Severity.WARNING: 2,
    Severity.CRITICAL: 3,
}


def _split_csv(value: Any) -> tuple[str, ...]:
    if value is None:
        return ()
    if isinstance(value, str):
        items = value.split(",")
    else:
        items = value

    normalized = []
    seen = set()
    for item in items:
        text = str(item).strip()
        if not text:
            continue
        if text not in seen:
            normalized.append(text)
            seen.add(text)
    return tuple(normalized)


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="forbid",
        case_sensitive=True,
    )

    database_url: str = Field(
        "postgresql+psycopg://postgres:postgres@localhost:5432/bn_monitor",
        validation_alias="DATABASE_URL",
    )
    binance_rest_url: str = Field("https://fapi.binance.com", validation_alias="BINANCE_REST_URL")
    binance_ws_url: str = Field("wss://fstream.binance.com/stream", validation_alias="BINANCE_WS_URL")
    universe_mode: UniverseMode = Field(UniverseMode.TOP_USDT, validation_alias="UNIVERSE_MODE")
    symbols_raw: str = Field("", validation_alias="SYMBOLS")
    alert_mode: AlertMode = Field(AlertMode.SHADOW, validation_alias="ALERT_MODE")
    discord_webhook_url: str = Field("", validation_alias="DISCORD_WEBHOOK_URL")
    discord_min_severity: Severity = Field(Severity.WARNING, validation_alias="DISCORD_MIN_SEVERITY")
    discord_alert_type_allowlist_raw: str = Field("", validation_alias="DISCORD_ALERT_TYPE_ALLOWLIST")
    data_retention_days: int = Field(30, gt=0, validation_alias="DATA_RETENTION_DAYS")
    price_threshold_bps: float = Field(100.0, gt=0, validation_alias="PRICE_THRESHOLD_BPS")
    volume_percentile_threshold: float = Field(
        0.95,
        ge=0,
        le=1,
        validation_alias="VOLUME_PERCENTILE_THRESHOLD",
    )
    volume_robust_z_threshold: float = Field(3.0, gt=0, validation_alias="VOLUME_ROBUST_Z_THRESHOLD")
    alert_cooldown_minutes: int = Field(10, gt=0, validation_alias="ALERT_COOLDOWN_MINUTES")
    rule_thresholds_raw: str = Field("{}", validation_alias="RULE_THRESHOLDS")

    @field_validator("database_url", "binance_rest_url", "binance_ws_url")
    @classmethod
    def require_non_empty(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("must not be empty")
        return value

    @model_validator(mode="after")
    def validate_cross_fields(self) -> Settings:
        if self.universe_mode == UniverseMode.EXPLICIT and not self.symbols:
            raise ValueError("SYMBOLS must be set when UNIVERSE_MODE=explicit")

        unknown_types = sorted(set(self.discord_alert_type_allowlist) - KNOWN_ALERT_TYPES)
        if unknown_types:
            raise ValueError(f"unknown alert_type in DISCORD_ALERT_TYPE_ALLOWLIST: {', '.join(unknown_types)}")

        raw = self.rule_thresholds_raw.strip()
        if raw:
            try:
                parsed = json.loads(raw)
            except json.JSONDecodeError as exc:
                raise ValueError(f"RULE_THRESHOLDS is not valid JSON: {exc}") from exc
            if not isinstance(parsed, dict):
                raise ValueError("RULE_THRESHOLDS must be a JSON object")
            for alert_type, rule_cfg in parsed.items():
                if alert_type not in KNOWN_RULE_THRESHOLDS:
                    raise ValueError(f"unknown alert_type in RULE_THRESHOLDS: {alert_type!r}")
                if not isinstance(rule_cfg, dict):
                    raise ValueError(f"RULE_THRESHOLDS[{alert_type!r}] must be a JSON object")
                unknown_keys = sorted(k for k in rule_cfg if k not in KNOWN_RULE_THRESHOLDS[alert_type])
                if unknown_keys:
                    raise ValueError(f"unknown key in RULE_THRESHOLDS[{alert_type!r}]: {', '.join(unknown_keys)}")
                for k, v in rule_cfg.items():
                    try:
                        Decimal(str(v))
                    except InvalidOperation:
                        raise ValueError(f"RULE_THRESHOLDS[{alert_type!r}][{k!r}] cannot be converted to Decimal: {v!r}")

        return self

    @property
    def symbols(self) -> tuple[str, ...]:
        symbols = []
        seen = set()
        for symbol in _split_csv(self.symbols_raw):
            normalized = symbol.upper()
            if normalized not in seen:
                symbols.append(normalized)
                seen.add(normalized)
        return tuple(symbols)

    @property
    def rule_thresholds(self) -> dict[str, dict[str, Decimal]]:
        raw = self.rule_thresholds_raw.strip()
        if not raw or raw == "{}":
            return {}
        return {
            alert_type: {k: Decimal(str(v)) for k, v in rule_cfg.items()}
            for alert_type, rule_cfg in json.loads(raw).items()
        }

    @property
    def discord_alert_type_allowlist(self) -> tuple[str, ...]:
        return _split_csv(self.discord_alert_type_allowlist_raw)

    def masked_dump(self) -> dict[str, Any]:
        data = self.model_dump(mode="json")
        data["symbols"] = self.symbols
        data["discord_alert_type_allowlist"] = self.discord_alert_type_allowlist
        del data["symbols_raw"]
        del data["discord_alert_type_allowlist_raw"]
        if data["discord_webhook_url"]:
            data["discord_webhook_url"] = "***"
        return data


def load_settings() -> Settings:
    return Settings()
