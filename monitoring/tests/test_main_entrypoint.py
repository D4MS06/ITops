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
