from http_test.ws_request import select_origin_header


def test_select_origin_none():
    """
    When no origin header is specified in the list of headers to be sent,
    we should return None as the origin, and the same list of headers as we
    received.
    """
    headers = [
        "Host: test.example.com",
        "Connection: Upgrade",
    ]

    origin, headers_no_origin = select_origin_header(headers)
    assert origin is None, f"No origin header selected, as none was there"
    assert len(headers) == len(headers_no_origin), f"No headers removed"


def test_select_origin_header():
    """
    When an origin header is specified in the list of headers to be sent,
    we return its value as origin, and remove it from the list of headers.
    """
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
    """
    Test that we can correctly detect the origin header when it's mixed case
    """
    headers = [
        "Host: test.example.com",
        "Connection: Upgrade",
        "oriGIN: test.example.com",
    ]

    origin, headers_no_origin = select_origin_header(headers)
    assert origin == "test.example.com", f"Mixed case origin header extracted successfully"
