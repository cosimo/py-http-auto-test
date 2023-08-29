from http_test.ws_request import select_origin_header


def test_select_origin_none():
    headers = [
        "Host: test.example.com",
        "Connection: Upgrade",
    ]

    origin, headers_no_origin = select_origin_header(headers)
    assert origin is None, f"No origin header selected, as none was there"
    assert len(headers) == len(headers_no_origin), f"No headers removed"


def test_select_origin_header():
    headers = [
        "Host: test.example.com",
        "Connection: Upgrade",
        "Origin: test.example.com",
    ]

    origin, headers_no_origin = select_origin_header(headers)
    assert origin == "test.example.com", f"Origin header extracted successfully"

    assert len(headers_no_origin) < len(headers), f"Origin header removed from headers list: {headers_no_origin}"

    assert (
        "Origin: test.example.com" not in headers_no_origin
    ), f"Origin header removed from headers list: {headers_no_origin}"


def test_select_origin_header_mixed_case():
    headers = [
        "Host: test.example.com",
        "Connection: Upgrade",
        "oriGIN: test.example.com",
    ]

    origin, headers_no_origin = select_origin_header(headers)
    assert origin == "test.example.com", f"Mixed case origin header extracted successfully"
