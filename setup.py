import os

from setuptools import setup

from http_test import __version__


def read(filename):
    fullpath = os.path.join(os.path.dirname(__file__), filename)
    return open(fullpath, "r", encoding="utf-8").read()


setup(
    name="py-http-auto-test",
    version=__version__,
    description="Python HTTP automated testing facility",
    long_description=read("README.md"),
    long_description_content_type="text/markdown",
    author="Cosimo Streppone",
    author_email="cosimo@streppone.it",
    url="https://github.com/cosimo/py-http-test",
    packages=["http_test"],
    license="MIT",
    install_requires=open("requirements.txt").readlines(),
    python_requires=">=3.8",
    scripts=["bin/http-test-runner.py"],
    classifiers=[
        "Development Status :: 4 - Beta",
        "Environment :: Console",
        "License :: OSI Approved :: MIT License",
        "Topic :: Utilities",
        "Operating System :: OS Independent",
    ],
)
