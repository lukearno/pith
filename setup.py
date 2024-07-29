import os
from setuptools import setup, find_packages


with open("README.md") as readme_file:
    README = str(readme_file.read().strip().strip("#").strip())

DESCRIPTION = README.split("\n")[0]
PROJECT = DESCRIPTION.split()[0]
ENTRYPOINTS = """
[console_scripts]
pith = pith.cli:run
""".strip()

setup(
    name=PROJECT,
    description=DESCRIPTION,
    long_description=README,
    author="Luke Arno",
    author_email="luke.arno@gmail.com",
    packages=find_packages(exclude=["tests"]),
    include_package_data=True,
    entry_points=ENTRYPOINTS,
)
