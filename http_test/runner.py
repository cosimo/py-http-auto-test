import os
from pathlib import Path

from http_test.spec import SpecFile, SpecTest

RED = "\033[91m"
GREEN = "\033[92m"
RESET = "\033[0m"


def run_specfiles(test_files, connect_to=None, verbose=False):
    fail_count = 0

    ok_mark = GREEN + "✓" + RESET
    ko_mark = RED + "✗" + RESET

    for test_filename in test_files:
        test_file = Path(test_filename)
        spec_file = SpecFile(path=test_file)
        tests = spec_file.load_tests()

        for test in tests:
            if connect_to:
                test["spec"]["config"]["connect_to"] = connect_to

            spec = SpecTest(name=test["name"], spec=test["spec"])
            is_success = spec.run()

            if verbose:
                print(f"{ok_mark if is_success else ko_mark} " f"{spec.describe()}")

            if not is_success:
                fail_count += 1

    return fail_count
