import pycurl
import pytest

from http_test.spec import SpecTest, verify_response


def test_verify_response_multiple_headers():
    """
    Regression test.
    We can match requirements on response headers when there's multiple
    instances of the same HTTP header in the response.
    """
    response = {
        "status_code": 200,
        "response_headers": {
            "content-type": "application/json",
            "strict-transport-security": [
                "strict-transport-security: max-age=900",
                "strict-transport-security: max-age=86400",
            ],
        },
    }

    requirements = {
        "headers": [
            "strict-transport-security: max-age=86400",
        ]
    }

    assert verify_response(response, requirements)


def test_verify_misspelled_requirement_name():
    """
    Verify that whenever the user misspells a match requirement (f.ex.
    `header` instead of `headers`, we throw an exception instead of silently
    succeeding the test.
    """
    response = {
        "status_code": 200,
        "response_headers": {
            "content-type": "application/json",
        },
    }

    requirements = {
        # This is incorrect, it should be `headers` instead
        "header": [
            "content-type: application/json",
        ]
    }

    with pytest.raises(ValueError):
        assert verify_response(response, requirements)


def test_skipped():
    """
    Verify that return values for skipped tests run() method are correct.
    """
    test = SpecTest(name="test", spec={"skip": True, "config": {}})
    is_success, fail_reason = test.run()

    assert is_success is True
    assert fail_reason == "skipped"


def test_verify_response_headers_absent_success():
    """
    Test that headers_absent correctly passes when specified headers are not present.
    """
    response = {
        "status_code": 200,
        "response_headers": {
            "content-type": "application/json",
            "server": "nginx/1.18.0",
        },
    }

    requirements = {
        "headers_absent": [
            "x-debug-info",
            "x-powered-by",
        ]
    }

    assert verify_response(response, requirements)


def test_verify_response_headers_absent_failure():
    """
    Test that headers_absent correctly fails when a specified header is present.
    """
    response = {
        "status_code": 200,
        "response_headers": {
            "content-type": "application/json",
            "x-debug-info": "enabled",
            "server": "nginx/1.18.0",
        },
    }

    requirements = {
        "headers_absent": [
            "x-debug-info",
        ]
    }

    with pytest.raises(AssertionError) as exc_info:
        verify_response(response, requirements)

    assert "Expected header 'x-debug-info' to be absent but it was found in response" in str(exc_info.value)


def test_verify_response_headers_absent_case_insensitive():
    """
    Test that headers_absent is case-insensitive for header names.
    """
    response = {
        "status_code": 200,
        "response_headers": {
            "Content-Type": "application/json",
            "X-Debug-Info": "enabled",
        },
    }

    requirements = {
        "headers_absent": [
            "x-debug-info",  # lowercase should match X-Debug-Info
        ]
    }

    with pytest.raises(AssertionError) as exc_info:
        verify_response(response, requirements)

    assert "Expected header 'x-debug-info' to be absent but it was found in response" in str(exc_info.value)


def test_verify_response_headers_absent_mixed_with_present():
    """
    Test that headers_absent works correctly when combined with regular headers requirement.
    """
    response = {
        "status_code": 200,
        "response_headers": {
            "content-type": "application/json",
            "server": "nginx/1.18.0",
        },
    }

    requirements = {
        "headers": [
            "content-type: application/json",
        ],
        "headers_absent": [
            "x-powered-by",
            "x-debug-info",
        ]
    }

    assert verify_response(response, requirements)
