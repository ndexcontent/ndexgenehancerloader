#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""The setup script."""
import os
import re
from setuptools import setup, find_packages


with open(os.path.join('ndexgenehancerloader', '__init__.py')) as ver_file:
    for line in ver_file:
        if line.startswith('__version__'):
            version=re.sub("'", "", line[line.index("'"):])

with open('README.rst') as readme_file:
    readme = readme_file.read()

with open('HISTORY.rst') as history_file:
    history = history_file.read()

requirements = ['ndex2',
                'ndexutil',
                'xlrd',
                'mygene',
                'pandas']

setup_requirements = []

test_requirements = ['xlwt']

setup(
    author="Sophie Liu",
    author_email='sol015@ucsd.edu',
    classifiers=[
        'Development Status :: 2 - Pre-Alpha',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Natural Language :: English',
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
    ],
    description="Loads GeneHancer database to NDEx",
    install_requires=requirements,
    license="MIT license",
    long_description=readme + '\n\n' + history,
    include_package_data=True,
    keywords='ndexgenehancerloader',
    name='ndexgenehancerloader',
    packages=find_packages(include=['ndexgenehancerloader']),
    package_dir={'ndexgenehancerloader': 'ndexgenehancerloader'},
    package_data={'ndexgenehancerloader': ['loadplan.json',
                                           'style.cx',
                                           'genetypes.json',
                                           'networkattributes.json']},
    scripts=[ 'ndexgenehancerloader/ndexloadgenehancer.py'],
    setup_requires=setup_requirements,
    test_suite='tests',
    tests_require=test_requirements,
    url='https://github.com/ceofy/ndexgenehancerloader',
    version=version,
    zip_safe=False,
)
