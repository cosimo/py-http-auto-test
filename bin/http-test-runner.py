#!/usr/bin/env python3

"""
Run the http spec tests in an arbitrary YAML file or files.
Why would you want to do this? You most likely want to run your tests
with pytest instead. That is why a `conftest.py` file is provided.

There are other use cases where you might want to run tests programmatically,
perhaps from another existing python program or script. In such case, this
small script provides a starting point for how to invoke the `http_test.runner`
module.
"""

import sys

import click

from http_test.runner import run_specfiles


@click.command()
@click.option(
    "test_files",
    "--test-file",
    "-f",
    required=True,
    multiple=True,
    type=click.Path(exists=True),
    help="Path to the YAML test file",
)
@click.option(
    "target_host",
    "--target-host",
    "-h",
    required=False,
    help="Works similarly to curl's --connect-to option. Typically used to send a set of test requests to an alternative IP address/port or hostname/port",
)
@click.option(
    "template_vars",
    "--var",
    "-var",
    multiple=True,
    help="Declare a variable to be used in the yaml test file (f.ex. use `url: {{ domain }}/test.html` in the yaml file and then pass `--var domain=example.com` to this script",
)
@click.option(
    "verbose",
    "--verbose",
    "-v",
    is_flag=True,
    help="Print verbose output",
)
def run_tests(test_files, target_host=None, template_vars=None, verbose=False):
    template_vars_dict = dict((x.split("=") for x in template_vars))
    fail_count = run_specfiles(test_files, target_host=target_host, template_vars=template_vars_dict, verbose=verbose)

    # We need to sys.exit() right here if we want our shell to be able to
    # get the exit code with the number of failed tests.
    # A sys.exit() after run_tests() is not going to propagate the exit code.
    sys.exit(fail_count)


if __name__ == "__main__":
    run_tests(auto_envvar_prefix="HTTPTEST")
