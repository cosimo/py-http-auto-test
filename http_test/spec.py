"""
This module deserializes the YAML spec files into a list of tests.
Each test can then be run with the `SpecTest.run()` method.

The pytest `conftest.py` plugin makes use of this module to
run the yaml tests as a pytest suite, though the running logic is
embedded in here.
"""

import os
import urllib.parse
from pathlib import Path

import yaml

from http_test.request import Request


class SpecFile:
    def __init__(self, path: Path):
        self.path = path

    def load_tests(self):
        test_config = yaml.safe_load(self.path.open())
        test_specs = test_config.get("tests", [])
        tests = []

        for spec in test_specs:
            spec["config"] = test_config
            test_name = spec["description"]
            tests.append(
                {
                    "name": test_name,
                    "spec": spec,
                }
            )

        return tests


class SpecTest:
    def __init__(self, name: str, spec: dict):
        self.name = name
        self.spec = spec
        self.test_result = []

    def describe(self):
        return f"{self.name} for url {self.spec['url']}"

    def run(self):
        test_config = self.spec["config"]
        test_spec = self.spec

        request: Request = request_from_spec(test_spec, test_config)
        result = request.fire()

        self.test_result = [result]

        requirements = test_spec.get("match")
        template_vars = test_config.get("template_vars")
        is_success = verify_response(result, requirements, template_vars)
        assert is_success, f"Failed: {test_spec.get('description')}"

        """
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

        is_http_200_expected = test_spec.get("match", {}).get("status", "") == str(200)
        compare_responses = is_http_200_expected

        if connect_to and compare_responses:
            import hashlib

            hash1 = hashlib.sha256()
            hash1.update(result.get("response_body"))

            hash2 = hashlib.sha256()
            hash2.update(result2.get("response_body"))

            assert hash1.hexdigest() == hash2.hexdigest(), f"Response object from connect-to doesn't match original"
        """

        return is_success


def _dump(result: dict):
    return yaml.safe_dump(result)


def get_httptest_env_variables():
    """
    Return a dict of all environment variables starting with `HTTPTEST_`.
    """
    httptest_vars = {}
    prefix = "HTTPTEST_"
    for key, value in os.environ.items():
        if key.startswith(prefix):
            name = key.replace(prefix, "").lower()
            httptest_vars[name] = value

    return httptest_vars


def replace_variables(s: str, vars: dict = None) -> str:
    import jinja2

    httptest_vars = get_httptest_env_variables()
    if vars:
        httptest_vars.update(vars)

    t = jinja2.Template(s)
    return t.render(**httptest_vars)


def verify_response(result: dict, requirements: dict, template_vars: dict = None) -> bool:
    if not requirements:
        return True

    for requirement in requirements.keys():
        if requirement == "status":
            status_code = result.get("status_code")
            expected_status_codes = requirements.get("status")
            if expected_status_codes and not isinstance(expected_status_codes, list):
                expected_status_codes = [expected_status_codes]
            assert (
                status_code in expected_status_codes
            ), f"Expected status codes {expected_status_codes}, got {status_code}"

        elif requirement == "headers":
            response_headers = result.get("response_headers")
            expected_headers = requirements.get("headers")

            for expected_header in expected_headers:
                header_name, expected_value = list(map(str.strip, expected_header.split(":", 1)))
                expected_value = replace_variables(expected_value, template_vars)
                # pprint(response_headers)
                actual_value = response_headers.get(header_name) or ""
                # print(f"Checking header '{header_name}'='{actual_value}' for value '{expected_value}'")
                assert (
                    expected_value.lower() in actual_value.lower()
                ), f"Expected header {header_name} to contain '{expected_value}' (was '{actual_value}')"

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
                expected_bytes = replace_variables(expected_string, template_vars).encode("utf-8")
                # Must be bytes vs bytes here
                assert (
                    expected_bytes in response_body
                ), f"Expected response body to contain '{expected_string}': {_dump(result)}"

    return True


def is_relative_url(url: str) -> bool:
    """
    Returns True if the given URL is relative.
    """
    return not urllib.parse.urlparse(url).scheme


def resolve_connect_to(url: str, test_config: dict) -> list:
    connect_to = test_config.get("connect_to")

    # The `HTTPTEST_TARGET_HOST` variable is special, it enables an "automatic"
    # `--connect-to` setting, as if we had specified `--connect-to` for [py]curl
    target_host = test_config.get("target_host", os.environ.get("HTTPTEST_TARGET_HOST"))
    parsed_url = urllib.parse.urlparse(url)

    if not connect_to and target_host:
        port = parsed_url.port if parsed_url.port else (443 if parsed_url.scheme in ("wss", "https") else 80)
        connect_to = [f"{parsed_url.hostname}:{port}:{target_host}"]

    if connect_to and not isinstance(connect_to, list):
        connect_to = [connect_to]

    if connect_to:
        template_vars = test_config.get("template_vars")
        connect_to = [replace_variables(e, template_vars) for e in connect_to]

    return connect_to


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
    base_url = test_config.get("base_url")

    url = test_spec.get("url")
    if is_relative_url(url):
        url = base_url + url

    template_vars = test_config.get("template_vars")
    url = replace_variables(url, template_vars)

    # This allows one to have dynamic --connect-to settings, such as:
    #
    #   connect_to:
    #     - "{{ host }}:443:{{ target }}"
    #
    # and using HTTPTEST_HOST and HTTPTEST_TARGET environment variables
    # to provide the dynamic values.
    connect_to = resolve_connect_to(url, test_config)

    method = test_spec.get("method", "GET")
    headers = test_spec.get("headers", [])
    use_http2 = test_spec.get("http2", False)
    verbose_output = test_spec.get("verbose", False)
    payload = test_spec.get("payload", None)

    if headers:
        headers = [replace_variables(h, template_vars) for h in headers]

    if verbose_output:
        print()

    r = Request(
        url=url,
        connect_to=connect_to,
        payload=payload,
        method=method,
        headers=headers,
        verbose=verbose_output,
        http2=use_http2,
    )

    return r
