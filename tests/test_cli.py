from __future__ import annotations

from contextlib import contextmanager
from pathlib import Path

from monitor import cli
from monitor.config import Settings


def settings_from_text(tmp_path: Path, text: str) -> Settings:
    env_file = tmp_path / ".env"
    env_file.write_text(text, encoding="utf-8")
    return Settings(_env_file=env_file)


def test_run_once_executes_one_monitor_cycle(monkeypatch, tmp_path: Path) -> None:
    settings = settings_from_text(tmp_path, "UNIVERSE_MODE=explicit\nSYMBOLS=SOLUSDT,BNBUSDT\n")
    calls = []

    @contextmanager
    def fake_session_scope(session_factory):
        yield "session"

    def fake_run_live_smoke(settings_arg, session, symbols, binance_client=None, send_discord=True):
        calls.append((settings_arg, session, symbols, binance_client, send_discord))
        return {"summary": {"total": 0, "by_type": {}, "by_severity": {}}}

    monkeypatch.setattr(cli, "load_settings", lambda: settings)
    monkeypatch.setattr(cli, "build_engine", lambda settings_arg: "engine")
    monkeypatch.setattr(cli, "build_session_factory", lambda engine: "session_factory")
    monkeypatch.setattr(cli, "session_scope", fake_session_scope)
    monkeypatch.setattr(cli, "run_live_smoke", fake_run_live_smoke)

    result = cli.main(["run", "--once", "--no-discord"])

    assert result == 0
    assert len(calls) == 1
    assert calls[0][:3] == (settings, "session", ("SOLUSDT", "BNBUSDT"))
    assert calls[0][3] is not None
    assert calls[0][4] is False


def test_run_requires_symbols_when_top_usdt_discovery_is_not_implemented(monkeypatch, tmp_path: Path) -> None:
    settings = settings_from_text(tmp_path, "")
    monkeypatch.setattr(cli, "load_settings", lambda: settings)

    try:
        cli.main(["run", "--once"])
    except SystemExit as exc:
        assert exc.code == 2
    else:
        raise AssertionError("run without symbols should exit")
