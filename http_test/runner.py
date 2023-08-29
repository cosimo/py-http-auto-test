from pathlib import Path

from http_test.spec import SpecFile, SpecTest


def run_specfiles(test_files, verbose=False):
    fail_count = 0

    for test_filename in test_files:
        test_file = Path(test_filename)
        spec_file = SpecFile(path=test_file)
        tests = spec_file.load_tests()

        for test in tests:
            spec = SpecTest(name=test["name"], spec=test["spec"])
            is_success = spec.run()

            if verbose:
                print(f"{'✓' if is_success else '✗'} {spec.describe()}")

            if not is_success:
                fail_count += 1

    return fail_count
