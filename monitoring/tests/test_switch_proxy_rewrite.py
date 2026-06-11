from urllib.parse import urlsplit

import httpx

from monitoring.api.app import (
    _build_switch_proxy_download_retry_queries,
    _decode_switch_proxy_chunked_body,
    _inject_switch_proxy_runtime_js,
    _is_switch_proxy_attachment_response,
    _is_switch_proxy_login_redirect,
    _is_switch_proxy_multiple_transfer_encoding_error,
    _rewrite_switch_proxy_xml,
    _rewrite_switch_proxy_html,
)


def test_switch_proxy_detects_attachment_content_disposition():
    headers = {"content-disposition": 'attachment; filename="startup.cfg"'}

    assert _is_switch_proxy_attachment_response(headers)


def test_switch_proxy_detects_filename_content_disposition_without_attachment():
    headers = {"content-disposition": 'inline; filename="startup.cfg"'}

    assert _is_switch_proxy_attachment_response(headers)


def test_switch_proxy_runtime_keeps_switch_menu_click_handlers_untouched():
    html = _inject_switch_proxy_runtime_js(
        html_text="<html><head></head><body></body></html>",
        proxy_prefix="/devices/switch/SW1/web-ui",
        base=urlsplit("https://192.168.10.10/"),
    )

    assert 'document.addEventListener("click"' not in html
    assert "window.location.assign" not in html
    assert "window.location.replace" not in html
    assert "XMLHttpRequest.prototype.open" in html
    assert "window.open = function(url)" in html


def test_switch_proxy_html_rewrite_does_not_target_non_markup_config_text():
    body = b"hostname core-switch\ninterface vlan 10\n"

    rewritten = _rewrite_switch_proxy_html(
        body=body,
        proxy_prefix="/devices/switch/SW1/web-ui",
        base=urlsplit("https://192.168.10.10/"),
        proxy_path="cgi/download_config",
    )

    assert rewritten == body


def test_switch_proxy_download_retry_queries_toggle_ssd_first():
    queries = _build_switch_proxy_download_retry_queries(
        "action=8&ssd=4&filename=system/images/active-image"
    )

    assert queries[0] == "action=8&ssd=2&filename=system/images/active-image"


def test_switch_proxy_login_redirect_detects_download_failure():
    response = httpx.Response(
        302,
        headers={"location": "/devices/switch/SW1/web-ui/csced39dd/hpe/config/login.htm"},
    )

    assert _is_switch_proxy_login_redirect(response)


def test_switch_proxy_detects_multiple_transfer_encoding_error():
    error = httpx.RemoteProtocolError("multiple Transfer-Encoding headers")

    assert _is_switch_proxy_multiple_transfer_encoding_error(error)


def test_switch_proxy_lenient_chunked_decoder():
    raw = b"4\r\nconf\r\n3\r\nig\n\r\n0\r\n\r\n"

    assert _decode_switch_proxy_chunked_body(raw) == b"config\n"


def test_switch_proxy_xml_uses_upstream_http_session_type():
    body = b"<ConnectedUserList><sessionType>4</sessionType></ConnectedUserList>"

    rewritten = _rewrite_switch_proxy_xml(
        body=body,
        proxy_prefix="/devices/switch/SW1/web-ui",
        client_scheme="http",
    )

    assert b"<sessionType>2</sessionType>" in rewritten
