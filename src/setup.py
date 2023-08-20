import pathlib
import os
from setuptools import find_packages, setup

HERE = os.environ["PWD"]
with open(f"{HERE}/../README.md") as f:
    README = f.read()
with open(f"{HERE}/requirements.txt") as f:
    required = f.read().splitlines()

setup(
    name="fastapi-elasticsearch",
    version="0.8.2",
    description="Query Utility for Elasticsearch",
    long_description=README,
    long_description_content_type="text/markdown",
    url="https://github.com/euler-io/fastapi-elasticsearch",
    license="LGPL-2.1 License",
    packages=find_packages(exclude=("development",)),
    install_requires=required,
)
