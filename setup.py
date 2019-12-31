#!/usr/bin/python3

import setuptools

with open("README.md", "r") as fh:
    long_description = fh.read()

setuptools.setup(
    name="diseaz-dsaflow",
    version="0.0.2",
    author="Dmitry Azhichakov",
    author_email="dazhichakov@gmail.com",
    description="Tools for my personal workflow",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/diseaz/dsaflow",
    packages=setuptools.find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    install_requires=[
        "diseaz-dsapy @ git+https://github.com/diseaz/dsapy.git",
    ],
    entry_points={
        "console_scripts": [
            "dsaflow=dsaflow.scripts.dsaflow:run",
            "jflow=jflow.scripts.jflow:run",
        ],
    },
)
