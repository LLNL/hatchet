
from setuptools import setup
from codecs import open
from os import path

here = path.abspath(path.dirname(__file__))

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

# Get the version in a safe way
# per python docs: https://packaging.python.org/guides/single-sourcing-package-version/
version = {}
with open("./roundtrip/version.py") as fp:
    exec(fp.read(), version)


setup(
    name="roundtrip-lib",
    version=version["__version__"],
    description="A Python library for loading JS visualizations into jupyter notebooks.",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/hdc-arizona/roundtrip",
    author="Connor Scully-Allison",
    author_email="cscullyallison@email.arizona.edu",
    license="MIT",
    keywords="",
    packages=[
        "roundtrip"
    ],
    install_requires=[
        "numpy",
        "pandas",
    ],
    include_package_data=True,
)