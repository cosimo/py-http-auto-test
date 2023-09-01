# py-http-auto-test: Python HTTP automated testing facility

## What's this?

This is a simple HTTP testing library for Python.

The main idea is to be able to write simple YAML files that describe a suite of HTTP tests, and then run them either as a standalone script or as a [pytest](https://docs.pytest.org/en/latest/) test suite, with the provided [conftest.py](./conftest.py) plugin.

A YAML test suite might look like this:

```yaml
base_url: https://mysite.example.com

tests:
  - url: "/"
    description: "Fetch the index page"
    match:
      status: 200
      body:
        - "<!DOCTYPE html>"
  - url: "/favicon.ico"
    description: "Ensure the favicon file is present and served with the correct content type"
    match:
      headers:
        - "content-type: image/x-icon"
      status: 200
  - ...
```

## Why?

Once upon a time, there was [http-cuke](https://github.com/cosimo/http-cuke) which I made as an attempt to free myself of having to write tests. At that time, people believed that BDD/cucumber would enable not-necessarily technical people to write business logic test suites. I have personally never seen this happen.

Instead of making the same mistake again, and learning from the past years of experience testing systems, I tried to write something that:

- makes use of a solid HTTP library: libcurl, pycurl
- covers websockets testing. [pycurl doesn't yet](https://github.com/pycurl/pycurl/issues/783)
- minimizes the amount of code one needs to write to run a test suite

## Some Use-Cases

- When building a new package image/AMI, it's nice to be able to spawn a new instance and get a simple and clear answer to the question: *Can I online this instance? Will things work?*
- Regression testing a web application
- Live testing of a running system every x minutes

## Requirements

See the [requirements.txt](requirements.txt) file for the full list of requirements. The main ones are:

- Python 3.8 or later
- The `libcurl4-openssl-dev` package on Debian-based systems, or `libcurl-devel` or whatever the equivalent on your system is, required to build `pycurl`
- `pycurl` version 7+
- `websockets` library to run tests against websockets

### Optional Requirements

- `pytest` if you want to run http tests as a pytest test suite

## Installation

```bash
sudo apt-get update -qq
# You need libcurl to build and install pycurl
sudo apt-get install -y libcurl4-openssl-dev
pip install --upgrade py-http-auto-test
```

## Usage

There are two main ways to use this library:
- standalone
- pytest

### Standalone

This distribution provides a `http-test-runner.py` script (usually installed in `/usr/local/bin`, or in your virtualenv's `bin` folder) that can be used to run one or more YAML test files.

Examples:

```bash
http-test-runner.py --help

http-test-runner.py --test-file website.yaml

# Run the tests but against an alternative IP address
# (this is similar to `MAP * <ip>` in Chrome or `--connect-to *:*:<ip>` in curl)
http-test-runner.py --test-file website.yaml --target-host 127.0.0.1
```

The library also supports template variables in the YAML files. This is useful if you want to define a set of tests for your web application, and then run them against different environments, for example:

```yaml
---
# YAML test file
base_url: "https://{{ hostname }}"
tests:
  - url: "/"
    description: "Index page exists and it's served correctly"
    ...
```

and then:

```bash
http-test-runner.py --test-file website.yaml --var "hostname=test.mydomain.com"
```

The `{{ hostname }}` variable will be replaced with `test.mydomain.com` in the test suite.

The template format is [jinja2](https://jinja.palletsprojects.com/en/).

### pytest

All that was described for the standalone case works also as a pytest test suite. You need to make sure the provided `conftest.py` plugin is found when you run `pytest`.

Example:

```bash
pytest -v ./test.yaml
```

If you need to pass on arguments or template variables, you can do so using environment variables prefixed with the string `HTTPTEST_`, as in:

```bash
HTTPTEST_TARGET_HOST="127.0.0.1" HTTPTEST_TEMPLATE_VARS="hostname=test.mydomain.com" pytest -v ./test.yaml
```

To pass on multiple environment variables, use a space character to separate multiple values, as in:

```bash
HTTPTEST_TARGET_HOST="127.0.0.1" HTTPTEST_TEMPLATE_VARS="hostname=test.mydomain.com protocol=https" pytest -v ./test.yaml
```

## Comprehensive Example of a Single Test

An HTTP test has a bunch of attributes, some of which are optional. The following is a semi-complete example:

```yaml
- url: "/index.html"

  description: "Verify that we can correctly download the index page as gzip-compressed response"

  headers:
    - "accept: text/html"
    - "accept-encoding: gzip"

  verbose: true   # false is the default
  http2: true     # false (http/1.1) is the default

  # Here is where you specify the test requirements
  match:

    # Response HTTP status must be 200 for the test to pass
    # This can also be a list of status codes
    status: 200

    # Verify that the response matches the following headers.
    # Header names will be matched regardless of upper or lower case.
    headers:
      - "content-type: text/html"
      - "content-encoding: gzip"

    # Verify that the response body contains the specified string patterns
    body:
      - "<!DOCTYPE html>"
      - "<h1>Hello</h1>"

    # Verify that the request took less than 500ms
    timing: 500ms
```
