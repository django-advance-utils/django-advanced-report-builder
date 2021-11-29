import setuptools
from setuptools import find_packages

with open("readme.md", "r") as fh:
    long_description = fh.read()

setuptools.setup(
    name="django-advance-query-builder",
    version="0.0.1",
    author="Thomas Turner",
    description="Django app that allows you to build reports from modals",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/django-advance-utils/django-advance-query-builder",
    include_package_data=True,
    packages=find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires='>=3.6',
)
