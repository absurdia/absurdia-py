import os
from codecs import open
from setuptools import setup, find_packages

here = os.path.abspath(os.path.dirname(__file__))

os.chdir(here)

with open(
    os.path.join(here, "README.md"), "r", encoding="utf-8"
) as fp:
    long_description = fp.read()

version_contents = {}
with open(os.path.join(here, "absurdia", "version.py"), encoding="utf-8") as f:
    exec(f.read(), version_contents)

setup(
    name="absurdia",
    version=version_contents["VERSION"],
    description="Python bindings for the Absurdia API",
    long_description=long_description,
    long_description_content_type='text/markdown',
    author="Absurdia",
    author_email="support@absurdia.markets",
    url="https://github.com/absurdia/absurdia-py",
    license="MIT",
    keywords="absurdia api trading",
    packages=find_packages(exclude=["tests", "tests.*"]),
    package_data={"absurdia": ["data/ca-certificates.crt"]},
    zip_safe=True,
    install_requires=[
        'click',
        'pydantic',
        'brotlipy',
        'psutil',
        "colorama",
        'httpx[http2] >= 0.21.2; python_version >= "3.4"',
    ],
    python_requires=">=3.7, !=3.0.*, !=3.1.*, !=3.2.*, !=3.3.*",
    entry_points={
        "console_scripts": [
            "absurdia = absurdia.cli:cli"
        ]
    },
    project_urls={
        "Bug Tracker": "https://github.com/absurdia/absurdia-py/issues",
        "Changes": "https://github.com/absurdia/absurdia-py/blob/master/CHANGELOG.md",
        "Source Code": "https://github.com/absurdia/absurdia-py",
    },
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.4",
        "Programming Language :: Python :: 3.5",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: Implementation :: PyPy",
        "Topic :: Software Development :: Libraries :: Python Modules",
    ],
    setup_requires=["wheel"],
)