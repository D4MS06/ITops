import os

from main import build_cli_parser, main


def test_cli_parser_defaults_to_server():
    args = build_cli_parser().parse_args([])
    assert args.mode == "server"
    assert args.host == "0.0.0.0"
    assert args.port == 8080
    assert args.reload is False


def test_main_dispatches_to_server(monkeypatch):
    calls = []
    monkeypatch.setattr("main.setup_logging", lambda *_args, **_kwargs: calls.append("logging"))
    monkeypatch.setattr(
        "main.run_server",
        lambda *, host, port, reload: calls.append(("server", host, port, reload)),
    )

    main(["--mode", "server", "--host", "0.0.0.0", "--port", "9000", "--reload"])

    assert calls == ["logging", ("server", "0.0.0.0", 9000, True)]


def test_main_applies_local_dev_defaults_when_pycharm_windows(monkeypatch):
    calls = []
    monkeypatch.delenv("NMP_DEV_LOCAL_AUTO_SETUP", raising=False)
    monkeypatch.delenv("NMP_DEV_SKIP_SETUP_WIZARD", raising=False)
    monkeypatch.delenv("NMP_DEV_FORCE_SQLITE_BACKEND", raising=False)
    monkeypatch.delenv("NMP_SETUP_SKIP_MARIADB_PROVISION", raising=False)
    monkeypatch.delenv("NMP_SETUP_SKIP_REVERSE_PROXY_SETUP", raising=False)
    monkeypatch.setenv("PYCHARM_HOSTED", "1")
    monkeypatch.setattr("main.setup_logging", lambda *_args, **_kwargs: calls.append("logging"))
    monkeypatch.setattr(
        "main.run_server",
        lambda *, host, port, reload: calls.append(("server", host, port, reload)),
    )
    monkeypatch.setattr("main.os.name", "nt", raising=False)

    main(["--mode", "server"])

    assert calls[0] == "logging"
    assert os.environ.get("NMP_DEV_SKIP_SETUP_WIZARD") == "1"
    assert os.environ.get("NMP_DEV_FORCE_SQLITE_BACKEND") == "1"
    assert os.environ.get("NMP_SETUP_SKIP_MARIADB_PROVISION") == "1"
    assert os.environ.get("NMP_SETUP_SKIP_REVERSE_PROXY_SETUP") == "1"
