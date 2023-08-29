import json
import os
import traceback
from pprint import pprint

import pytest
import yaml

from request import Request


def pytest_collect_file(parent, file_path):
    if file_path.suffix == ".yaml" and file_path.name.startswith("test"):
        return YamlFile.from_parent(parent, path=file_path)


class YamlFile(pytest.File):
    def collect(self):
        import yaml

        test_config = yaml.safe_load(self.path.open())
        test_specs = test_config.get("tests", [])

        for spec in test_specs:
            spec["config"] = test_config
            test_name = spec["description"]
            yield YamlTest.from_parent(self, name=test_name, spec=spec)


class YamlTest(pytest.Item):
    def __init__(self, *, spec, **kwargs):
        super().__init__(**kwargs)
        self.spec = spec
        self.test_result = None

    def runtest(self):
        test_config = self.spec["config"]
        test_spec = self.spec

        connect_to = test_config.get("connect_to")
        request: Request = request_from_spec(test_spec, test_config)
        result = request.fire()

        self.test_result = [result]

        requirements = test_spec.get("match")
        is_success = verify_response(result, requirements)
        assert is_success, f"Failed: {test_spec.get('description')}"

        # Repeat the same test connecting to a different IP address
        # and comparing the two responses
        if connect_to:
            request2 = request_from_spec(test_spec, test_config)
            request2.request_id = request.request_id + "/CT"
            request2.connect_to = connect_to
            result2 = request2.fire()

            self.test_result.append(result2)

            is_success = verify_response(result2, requirements)
            assert is_success, f"Failed: {test_spec.get('description')} (connect_to: {connect_to})"

        compare_responses = test_spec.get("match", {}).get("status", "") == str(200)
        if connect_to and compare_responses:
            import hashlib

            hash1 = hashlib.sha256()
            hash1.update(result.get("response_body"))

            hash2 = hashlib.sha256()
            hash2.update(result2.get("response_body"))

            assert hash1.hexdigest() == hash2.hexdigest(), f"Response object from connect-to doesn't match original"

    def repr_failure(self, excinfo):
        """Called when self.runtest() raises an exception."""
        return str(excinfo.value) + "\n" + "".join((traceback.format_tb(excinfo.tb, limit=10)))

    def reportinfo(self):
        """
        This is only seen if a test fails
        """
        return (
            self.path,  # path to the test file
            0,  # no line number
            f"Test: {self.spec['description']} for url {self.spec['url']}",
        )


def _dump(result: dict):
    return yaml.safe_dump(result)


def verify_response(result: dict, requirements: list) -> bool:
    if not requirements:
        return True

    for requirement in requirements:
        if requirement == "status":
            status_code = result.get("status_code")
            expected_status_code = requirements.get("status")
            assert (
                status_code == expected_status_code
            ), f"Expected status code {expected_status_code}, got {status_code}"

        elif requirement == "headers":
            response_headers = result.get("response_headers")
            expected_headers = requirements.get("headers")

            for expected_header in expected_headers:
                header_name, expected_value = list(map(str.strip, expected_header.split(":", 1)))
                expected_value = expected_value.replace("{{ domain }}", get_domain())
                # pprint(response_headers)
                actual_value = response_headers.get(header_name) or ""
                # print(f"Checking header '{header_name}'='{actual_value}' for value '{expected_value}'")
                assert (
                    expected_value.lower() in actual_value.lower()
                ), f"Expected header {actual_value} to contain '{expected_value}'"

        elif requirement == "timing":
            elapsed_time_s = result.get("elapsed")
            max_allowed_time = requirements.get("timing")
            if max_allowed_time.endswith("ms"):
                max_allowed_time_s = float(max_allowed_time[:-2]) / 1000
            else:
                max_allowed_time_s = max_allowed_time
            assert (
                elapsed_time_s < max_allowed_time_s
            ), f"Expected elapsed time to be less than {max_allowed_time_s}s, got {elapsed_time_s}s instead"

        elif requirement == "body":
            expected_strings = requirements.get("body")
            response_body = result.get("response_body_decoded")
            for expected_string in expected_strings:
                expected_bytes = expected_string.replace("{{ domain }}", get_domain()).encode("utf-8")
                # Must be bytes vs bytes here
                assert (
                    expected_bytes in response_body
                ), f"Expected response body to contain '{expected_string}': {_dump(result)}"

    return True


def get_domain() -> str:
    return os.environ.get("TEST_DOMAIN", "kahoot-experimental.it")


def request_from_spec(test_spec: dict, test_config: dict) -> Request:
    """
    Transform the following YAML spec test into a Request object.

    ```
    url: /
    headers:
      - "accept-encoding: br"
    match:
      status: 200
      headers:
        content-type: text/html
        server: openresty
    ```
    """
    domain = get_domain()
    base_url = test_config.get("base_url")

    url = test_spec.get("url")
    url = url if url.startswith("http") or url.startswith("wss://") \
        else base_url + url

    def replace_domain(s: str) -> str:
        return s.replace("{{ domain }}", domain)

    url = replace_domain(url)
    method = test_spec.get("method", "GET")
    headers = test_spec.get("headers", [])
    use_http2 = test_spec.get("http2", False)
    verbose_output = test_spec.get("verbose", False)
    payload = test_spec.get("payload", None)

    if headers:
        headers = list(map(replace_domain, headers))

    if verbose_output:
        print()

    r = Request(
        url=url,
        payload=payload,
        method=method,
        headers=headers,
        verbose=verbose_output,
        http2=use_http2,
    )

    return r
