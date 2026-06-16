import asyncio
from types import SimpleNamespace
from urllib.parse import urlsplit

import httpx

import monitoring.api.app as app_module
from monitoring.api.app import (
    _build_switch_proxy_successful_load_status_body,
    _build_switch_proxy_download_retry_queries,
    _classify_switch_proxy_load_status,
    _decode_switch_proxy_chunked_body,
    _inject_switch_proxy_runtime_js,
    _is_switch_proxy_attachment_response,
    _is_switch_proxy_image_download_false_abort,
    _is_switch_proxy_login_redirect,
    _is_switch_proxy_multiple_transfer_encoding_error,
    _resolve_switch_base_url,
    _resolve_switch_proxy_session,
    _strip_proxy_token_from_query,
    _rewrite_switch_proxy_recent_download_load_status,
    _rewrite_switch_proxy_html,
    _rewrite_switch_proxy_xml,
    _rewrite_switch_proxy_set_cookie,
    _request_switch_proxy_lenient_sync,
    _send_switch_proxy_request,
    _switch_proxy_response_has_download_body,
    _switch_proxy_session_cookie_value,
    _strip_switch_proxy_internal_cookies,
)


def test_switch_proxy_detects_attachment_content_disposition():
    headers = {"content-disposition": 'attachment; filename="startup.cfg"'}

    assert _is_switch_proxy_attachment_response(headers)


def test_switch_proxy_strips_internal_and_empty_duplicate_cookies():
    cookie_header = (
        "itops_switch_proxy_token=abc; "
        "SID=valid-session; "
        "itops_switch_proxy_prefix=\"/devices/switch/SW1/web-ui\"; "
        "token=1781517103459; "
        "SID="
    )

    assert _strip_switch_proxy_internal_cookies(cookie_header) == "SID=valid-session"


def test_switch_proxy_keeps_last_non_empty_duplicate_cookie_value():
    cookie_header = "SID=old-session; theme=dark; SID=new-session"

    assert _strip_switch_proxy_internal_cookies(cookie_header) == "SID=new-session; theme=dark"


def test_switch_proxy_session_prefers_cookie_token_over_query_token():
    seen_tokens = []

    class Auth:
        def get_session(self, token):
            seen_tokens.append(token)
            if token == "cookie-itops-token":
                return SimpleNamespace(subject="admin", token=token)
            return None

    class Logs:
        def subject_has_module(self, *, subject, module_code):
            return subject == "admin" and module_code == "monitoring"

    session = _resolve_switch_proxy_session(
        api=SimpleNamespace(auth=Auth(), logs=Logs()),
        authorization=None,
        token="switch-download-token",
        cookie_token="cookie-itops-token",
    )

    assert session.token == "cookie-itops-token"
    assert seen_tokens == ["cookie-itops-token"]


def test_switch_proxy_session_falls_back_to_query_token_when_cookie_is_stale():
    seen_tokens = []

    class Auth:
        def get_session(self, token):
            seen_tokens.append(token)
            if token == "fresh-query-itops-token":
                return SimpleNamespace(subject="admin", token=token)
            return None

    class Logs:
        def subject_has_module(self, *, subject, module_code):
            return subject == "admin" and module_code == "monitoring"

    session = _resolve_switch_proxy_session(
        api=SimpleNamespace(auth=Auth(), logs=Logs()),
        authorization=None,
        token="fresh-query-itops-token",
        cookie_token="stale-cookie-itops-token",
    )

    assert session.token == "fresh-query-itops-token"
    assert seen_tokens == ["stale-cookie-itops-token", "fresh-query-itops-token"]


def test_switch_proxy_session_cookie_uses_resolved_session_token():
    session = SimpleNamespace(token="fresh-itops-token")

    assert _switch_proxy_session_cookie_value(session) == "fresh-itops-token"


def test_switch_proxy_deletes_upstream_download_token_cookie():
    rewritten = _rewrite_switch_proxy_set_cookie(
        value="token=1781517103459; Path=/",
        proxy_prefix="/devices/switch/SW1/web-ui",
    )

    assert rewritten == "token=; Max-Age=0; Path=/devices/switch/SW1/web-ui/"


def test_switch_proxy_query_keeps_switch_download_token():
    query = "name=hp1820.cfg&file=/mnt/download/hp1820.cfg&token=1781513265883"

    assert _strip_proxy_token_from_query(query, auth_token="cookie-itops-token") == query


def test_switch_proxy_query_strips_only_matching_itops_auth_token():
    query = "token=itops-token&name=hp1820.cfg"

    assert _strip_proxy_token_from_query(query, auth_token="itops-token") == "name=hp1820.cfg"


def test_switch_proxy_shared_client_does_not_inject_cookie_jar():
    async def run_scenario():
        seen_cookies = []

        def handler(request):
            seen_cookies.append(request.headers.get("cookie"))
            return httpx.Response(200, headers={"set-cookie": "SID=stale-upstream; Path=/"}, text="ok")

        async with httpx.AsyncClient(
            transport=httpx.MockTransport(handler),
            base_url="https://switch.local",
        ) as client:
            await client.get("/seed-cookie")
            await _send_switch_proxy_request(
                client=client,
                method="GET",
                target_url="https://switch.local/no-browser-cookie",
                headers={},
            )
            await _send_switch_proxy_request(
                client=client,
                method="GET",
                target_url="https://switch.local/browser-cookie",
                headers={"Cookie": "SID=browser-session"},
            )

        return seen_cookies

    assert asyncio.run(run_scenario()) == [None, None, "SID=browser-session"]


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


def test_switch_proxy_base_url_defaults_to_http():
    base = _resolve_switch_base_url({"ip": "192.168.0.40", "device_subtype": "switch"})

    assert base.geturl() == "http://192.168.0.40/"


def test_switch_proxy_base_url_adds_http_scheme_to_bare_web_url():
    base = _resolve_switch_base_url(
        {"ip": "192.168.0.40", "device_subtype": "switch", "web_url": "192.168.0.40/custom"}
    )

    assert base.geturl() == "http://192.168.0.40/custom"


def test_switch_proxy_base_url_preserves_configured_https_scheme():
    base = _resolve_switch_base_url(
        {"ip": "192.168.0.40", "device_subtype": "switch", "web_url": "https://192.168.0.40"}
    )

    assert base.geturl() == "https://192.168.0.40/"


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


def test_switch_proxy_download_retry_queries_try_alternate_image_name():
    queries = _build_switch_proxy_download_retry_queries(
        "action=1&ssd=4&filename=system/images/inactive-image"
    )

    assert queries == [
        "action=1&ssd=2&filename=system/images/inactive-image",
        "action=1&ssd=4&filename=system/images/active-image",
        "action=1&ssd=2&filename=system/images/active-image",
        "action=8&ssd=4&filename=system/images/inactive-image",
        "action=8&ssd=2&filename=system/images/inactive-image",
        "action=8&ssd=4&filename=system/images/active-image",
        "action=8&ssd=2&filename=system/images/active-image",
    ]


def test_switch_proxy_login_redirect_detects_download_failure():
    response = httpx.Response(
        302,
        headers={"location": "/devices/switch/SW1/web-ui/csced39dd/hpe/config/login.htm"},
    )

    assert _is_switch_proxy_login_redirect(response)


def test_switch_proxy_detects_multiple_transfer_encoding_error():
    error = httpx.RemoteProtocolError("multiple Transfer-Encoding headers")

    assert _is_switch_proxy_multiple_transfer_encoding_error(error)


def test_switch_proxy_detects_incomplete_chunked_download_error():
    error = httpx.RemoteProtocolError("peer closed connection without sending complete message body (incomplete chunked read)")

    assert _is_switch_proxy_multiple_transfer_encoding_error(error)


def test_switch_proxy_lenient_chunked_decoder():
    raw = b"4\r\nconf\r\n3\r\nig\n\r\n0\r\n\r\n"

    assert _decode_switch_proxy_chunked_body(raw) == b"config\n"


def test_switch_proxy_lenient_request_reads_keep_alive_chunked_response(monkeypatch):
    class FakeSocket:
        def __init__(self):
            self.sent = b""
            self.recv_chunks = [
                (
                    b"HTTP/1.1 200 OK\r\n"
                    b"Content-Disposition: attachment;filename=image1.bin\r\n"
                    b"Content-Type: application/octet-stream\r\n"
                    b"Transfer-Encoding: chunked\r\n"
                    b"Transfer-Encoding: chunked\r\n"
                    b"Connection: Keep-Alive\r\n"
                    b"\r\n"
                    b"5\r\nhello\r\n"
                ),
                b"6\r\n world\r\n",
                b"0\r\n\r\n",
            ]

        def settimeout(self, _timeout):
            return None

        def sendall(self, data):
            self.sent += data

        def recv(self, _size):
            if self.recv_chunks:
                return self.recv_chunks.pop(0)
            raise app_module.socket.timeout()

        def close(self):
            return None

    fake_socket = FakeSocket()
    monkeypatch.setattr(app_module.socket, "create_connection", lambda *_args, **_kwargs: fake_socket)

    response = _request_switch_proxy_lenient_sync(
        method="GET",
        target_url="http://192.168.0.40/csced39dd/hpe/http_download?action=8",
        headers={"Cookie": "sessionID=abc"},
    )

    assert response.status_code == 200
    assert response.content == b"hello world"
    assert b"Accept-Encoding: gzip, deflate\r\n" in fake_socket.sent
    assert b"Connection: keep-alive\r\n" in fake_socket.sent


def test_switch_proxy_xml_uses_browser_https_session_type():
    body = b"<ConnectedUserList><sessionType>4</sessionType></ConnectedUserList>"

    rewritten = _rewrite_switch_proxy_xml(
        body=body,
        proxy_prefix="/devices/switch/SW1/web-ui",
        client_scheme="https",
    )

    assert b"<sessionType>4</sessionType>" in rewritten


def test_switch_proxy_rewrites_false_aborted_load_status_after_download():
    body = (
        b"<ResponseData><DeviceConfiguration><LoadStatus type=\"section\">"
        b"<copyStatusType>3</copyStatusType>"
        b"<bytesTransfered>12288</bytesTransfered>"
        b"<errorMessage>Copy: Copy process aborted by application</errorMessage>"
        b"</LoadStatus></DeviceConfiguration><ActionStatus><requestURL>LoadStatus</requestURL>"
        b"<statusCode></statusCode></ActionStatus></ResponseData>"
    )

    rewritten = _rewrite_switch_proxy_recent_download_load_status(body)

    assert b"Copy process aborted" not in rewritten
    assert b"<LoadStatus type=\"section\">" in rewritten
    assert b"<copyStatusType>" not in rewritten
    assert b"<statusCode>0</statusCode>" in rewritten
    assert b"<deviceStatusCode>0</deviceStatusCode>" in rewritten
    assert b"<statusString>OK</statusString>" in rewritten


def test_switch_proxy_detects_image_download_false_abort_load_status():
    body = (
        b"<ResponseData><DeviceConfiguration><LoadStatus type=\"section\">"
        b"<sourceFileName>system/images/image1.bin</sourceFileName>"
        b"<sourceFileType>8</sourceFileType>"
        b"<destinationFileName>system/images/image1.bin</destinationFileName>"
        b"<copyStatusType>3</copyStatusType>"
        b"<bytesTransfered>798720</bytesTransfered>"
        b"<totalSize>0</totalSize>"
        b"<errorMessage>Copy: Copy process aborted by application</errorMessage>"
        b"</LoadStatus></DeviceConfiguration></ResponseData>"
    )

    assert _is_switch_proxy_image_download_false_abort(body)


def test_switch_proxy_rewrites_image_false_abort_to_completed_load_status():
    body = (
        b"<ResponseData><DeviceConfiguration><LoadStatus type=\"section\">"
        b"<sourceFileName>system/images/image1.bin</sourceFileName>"
        b"<sourceFileType>8</sourceFileType>"
        b"<destinationFileName>system/images/image1.bin</destinationFileName>"
        b"<destinationFileType>1</destinationFileType>"
        b"<copyStatusType>3</copyStatusType>"
        b"<bytesTransfered>798720</bytesTransfered>"
        b"<totalSize>34227090</totalSize>"
        b"<errorMessage>Copy: Copy process aborted by application</errorMessage>"
        b"</LoadStatus></DeviceConfiguration><ActionStatus><requestURL>LoadStatus</requestURL>"
        b"<statusCode></statusCode></ActionStatus></ResponseData>"
    )

    rewritten = _rewrite_switch_proxy_recent_download_load_status(body)

    assert b"<copyStatusType>5</copyStatusType>" in rewritten
    assert b"<bytesTransfered>34227090</bytesTransfered>" in rewritten
    assert b"<totalSize>0</totalSize>" in rewritten
    assert b"Copy process aborted" not in rewritten


def test_switch_proxy_successful_load_status_body_is_ok():
    body = _build_switch_proxy_successful_load_status_body()

    assert b"<requestURL>LoadStatus</requestURL>" in body
    assert b"<copyStatusType>5</copyStatusType>" in body
    assert b"<statusCode></statusCode>" in body
    assert _classify_switch_proxy_load_status(body) == "copyStatusType-5"


def test_switch_proxy_rewrites_stuck_active_load_status_after_download():
    body = (
        b"<?xml version=\"1.0\" encoding=\"UTF-8\" ?>"
        b"<ResponseData><DeviceConfiguration><version>1.0</version>"
        b"<LoadStatus type=\"section\">"
        b"<copyStatusType>1</copyStatusType>"
        b"<bytesTransfered>800000</bytesTransfered>"
        b"</LoadStatus></DeviceConfiguration>"
        b"<ActionStatus><requestURL>LoadStatus</requestURL>"
        b"<statusCode></statusCode></ActionStatus></ResponseData>"
    )

    rewritten = _rewrite_switch_proxy_recent_download_load_status(body)

    assert b"<copyStatusType>" not in rewritten
    assert b"<bytesTransfered>" not in rewritten
    assert b"<statusCode>0</statusCode>" in rewritten
    assert b"<deviceStatusCode>0</deviceStatusCode>" in rewritten
    assert b"<statusString>OK</statusString>" in rewritten


def test_switch_proxy_classifies_empty_load_status():
    body = b"<ResponseData><LoadStatus type=\"section\"> </LoadStatus></ResponseData>"

    assert _classify_switch_proxy_load_status(body) == "empty"


def test_switch_proxy_classifies_copy_status_type():
    body = b"<ResponseData><LoadStatus type=\"section\"><copyStatusType>2</copyStatusType></LoadStatus></ResponseData>"

    assert _classify_switch_proxy_load_status(body) == "copyStatusType-2"


def test_switch_proxy_download_body_detects_content_length_header():
    assert _switch_proxy_response_has_download_body(
        response_body=b"",
        headers={"content-length": "800000"},
    )
