# -*- coding: utf-8 -*-

# SPDX-FileCopyrightText: 2016-2019 The Atlite Authors
#
# SPDX-License-Identifier: GPL-3.0-or-later

from setuptools import setup, find_packages
from codecs import open

with open('README.rst', encoding='utf-8') as f:
    long_description = f.read()

exec(open('atlite/_version.py').read())

setup(
    name='atlite',
    version=__version__,
    author='The Atlite Authors',
    author_email='coroa@posteo.de',
    description='Atlite helps you to convert weather data into energy systems model data.',
    long_description=long_description,
    url='https://github.com/PyPSA/atlite',
    license='GPLv3',
    packages=find_packages(exclude=['doc', 'test']),
    include_package_data=True,
    python_requires='~=3.6',
    install_requires=['numpy',
                      'scipy',
                      'pandas>=0.22',
                      'bottleneck',
                      'numexpr',
                      'xarray>=0.11.2',
                      'netcdf4',
                      'dask>=0.18.0',
                      'rasterio',
                      'requests',
                      'rtree',
                      "pyyaml",
                      "toolz",
                      "python-dateutil",
                      'shapely',
                      'toolz',
                      'progressbar2',
                      'pyproj>=2',
                      'geopandas',
                      'cdsapi'],
    extras_require = {
        "docs": ["numpydoc",
                 "sphinx", "sphinx_rtd_theme", "nbsphinx"]
    },
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Environment :: Console',
        'Intended Audience :: Science/Research',
        'License :: OSI Approved :: GNU General Public License v3 or later (GPLv3+)',
        'Natural Language :: English',
        'Operating System :: OS Independent',
    ])
