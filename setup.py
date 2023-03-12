from tonoi.misc import Misc
from setuptools import setup

setup_attrs = {
    "name": "tonoi",
    "version": Misc.util_version,
    "description": Misc.util_description,
    "long_description": Misc.util_description,
    "url": "https://www.github.com/Justaus3r/tonoi",
    "author": "Justaus3r",
    "license": "GPLV3",
    "classifiers": [
        "Development Status :: 5 - Production/Stable",
        "Environment :: Console",
        "Intended Audience :: Education",
        "License :: OSI Approved :: GNU General Public License v3 or later (GPLv3+)",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
    ],
    "project_urls": {"Homepage": "https://www.github.com/Justaus3r/tonoi"},
    "packages": ["tonoi"],
    "python_requires": ">=3",
    "entry_points": {"console_scripts": ["tonoi=tonoi.tonoi:main_entry"]},
}


setup(**setup_attrs)
