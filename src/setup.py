from setuptools import setup, find_packages
import os
import pathlib

HERE = pathlib.Path(__file__).parent
README = (HERE / "../README.md").read_text()

required = (HERE / "requirements.txt").read_text().splitlines()

setup(
    name="fastapi-elasticsearch",
    version="0.1.0",
    description="Query Utility for Elasticsearch",
    long_description=README,
    long_description_content_type="text/markdown",
    url="https://github.com/euler-io/fastapi-elasticsearch",
    license="LGPL-2.1 License",
    packages=find_packages(exclude=("development",)),
    install_requires=required,
)