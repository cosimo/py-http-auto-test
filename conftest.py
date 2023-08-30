"""
Pytest plugin to load http_test tests from YAML files

Here's an example yaml test file:

```yaml
---
base_url: "https://httpbin.org"

tests:
  - url: "/get"
    description: "Test GET request"
    method: "GET"
    headers:
      - "Accept: application/json"
    match:
      status: 200
      headers:
        - "content-type: application/json"
      timing: 5000ms
  - ...
```

"""
import traceback

import pytest

from http_test.spec import SpecFile, SpecTest


def pytest_collect_file(parent, file_path):
    if file_path.suffix == ".yaml" and file_path.name.startswith("test"):
        return YamlFile.from_parent(parent, path=file_path)


class YamlFile(pytest.File):
    def collect(self):
        for test in SpecFile(path=self.path).load_tests():
            yield YamlTest.from_parent(self, name=test["name"], spec=test["spec"])


class YamlTest(pytest.Item):
    def __init__(self, *, spec, **kwargs):
        super().__init__(**kwargs)
        self.spec = SpecTest(name=spec.get("description", ""), spec=spec)

    def runtest(self):
        self.spec.run()

    def repr_failure(self, excinfo):
        """Called when self.runtest() raises an exception."""
        return f"Exception {excinfo.type.__qualname__} ({excinfo.type}):\n" f"{excinfo.value}\n" + "".join(
            (traceback.format_tb(excinfo.tb, limit=10))
        )

    def reportinfo(self):
        """
        This is only seen if a test fails
        """
        return (self.path, 0, self.spec.describe())  # path to the test file  # no line number
