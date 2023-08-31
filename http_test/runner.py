import logging
from pathlib import Path

from http_test.spec import SpecFile, SpecTest

RED = "\033[91m"
GREEN = "\033[92m"
RESET = "\033[0m"


def inject_test_config_dict(test: dict, target_host: str, template_vars: dict) -> None:
    """
    This is a bad kludge to keep the conftest.py pytest plugin working

    Since we can't pass three parameters to the PyTest.Item instance, we
    augment the single test dictionary with an additional "config" key,
    which we fill up with `base_url`, `connect_to`, and whichever upper level
    variables.

    Not happy with this disgusting hack, we also add another
    key, `template_vars`, which is a dictionary of variables that can be
    used in various attributes of the yaml file, such as `url`, `headers`, and
    others. This makes the yaml test files parametric, which is super handy
    if you want to test different environments with the same test files.
    """
    config = test["spec"].get("config", dict())
    if target_host:
        config["target_host"] = target_host
    if template_vars:
        config["template_vars"] = template_vars

    if config:
        test["spec"]["config"] = config

    return


def run_specfiles(
    test_files: list,
    target_host: str = None,
    template_vars: dict = None,
    verbose: bool = False,
):
    fail_count = 0

    ok_mark = GREEN + "✓" + RESET
    ko_mark = RED + "✗" + RESET

    for test_filename in test_files:
        test_file = Path(test_filename)
        spec_file = SpecFile(path=test_file)
        tests = spec_file.load_tests()

        for test in tests:
            inject_test_config_dict(test, target_host, template_vars)
            spec = SpecTest(name=test["name"], spec=test["spec"])

            try:
                is_success = spec.run()
                fail_reason = None
            except AssertionError as e:
                is_success = False
                fail_reason = str(e)

            if verbose:
                print(f"{ok_mark if is_success else ko_mark} " f"{spec.describe()}")
                if fail_reason:
                    print(f"    {RED}{fail_reason}{RESET}")

            if not is_success:
                fail_count += 1

    return fail_count
