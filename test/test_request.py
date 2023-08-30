from http_test.request import Request


def test_resolve_connect_to_default_ports():
    """
    TODO
    """
    r = Request(
        url="https://test.example.com",
        connect_to=["test.example.com:443:1.2.3.4"],
    )

    host, port = r.resolve_connect_to()
    assert host == "1.2.3.4"
    assert port == 443

    r = Request(
        url="http://test.example.com",
        connect_to=["test.example.com:80:1.2.3.4"],
    )

    host, port = r.resolve_connect_to()
    assert host == "1.2.3.4"
    assert port == 80

    r = Request(
        url="https://test.example.com",
        connect_to=[
            "test.example.com:80:1.2.3.4",
            "test.example.com:443:1.2.3.4",
        ],
    )

    host, port = r.resolve_connect_to()
    assert host == "1.2.3.4"
    assert port == 443


def test_resolve_connect_to_wss_scheme():
    r = Request(
        url="wss://test.example.com/ws/",
        connect_to=["test.example.com:443:1.2.3.4"],
    )

    host, port = r.resolve_connect_to()
    assert host == "1.2.3.4"
    assert port == 443, "When using wss:// scheme, the default port should be 443"


def test_resolve_connect_to_with_explicit_port():
    """
    TODO
    """
    r = Request(
        url="https://test.example.com",
        connect_to=["test.example.com:443:1.2.3.4:8000"],
    )

    host, port = r.resolve_connect_to()
    assert host == "1.2.3.4"
    assert port == 8000


def test_resolve_connect_to_no_matching_entries():
    """
    TODO
    """
    r = Request(
        url="https://test.example.com",
        connect_to=[
            "test1.example.com:443:1.2.3.4"
            "test2.example.com:443:2.3.4.5"
            "test3.example.com:443:1.2.3.4:8000"
            "test4.example.com:443:2.3.4.5:8001"
        ],
    )

    host, port = r.resolve_connect_to()
    assert host == "test.example.com"
    assert port == 443
