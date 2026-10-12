# -*- coding: utf-8 -*-

# Copyright 2017 Aaron M. Hosford
# See LICENSE.txt for licensing information.

import os
import warnings

from setuptools import setup, find_packages


def get_long_description():
    rst_path = os.path.join(os.path.dirname(__file__), 'README.rst')
    md_path = os.path.join(os.path.dirname(__file__), 'README.md')

    try:
        # Imported here to avoid creating a dependency in the setup.py
        # if the .rst file already exists.

        # noinspection PyUnresolvedReferences
        from pypandoc.pandoc_download import download_pandoc

        download_pandoc()

        # noinspection PyUnresolvedReferences
        from pypandoc import convert_file
    except ImportError:
        warnings.warn("Module pypandoc not installed. Using markdown formatting.")
    else:
        # pandoc, you rock...
        rst_content = convert_file(md_path, 'rst')
        with open(rst_path, 'w') as rst_file:
            rst_file.write(rst_content)

    if os.path.isfile(rst_path):
        with open(rst_path) as rst_file:
            return rst_file.read()
    else:
        # It will be messy, but it's better than nothing...
        with open(md_path) as md_file:
            return md_file.read()


def get_metadata():
    about_path = os.path.join(os.path.dirname(__file__), 'vert', '__about__.py')
    results = {}
    with open(about_path) as about_file:
        exec(about_file.read(), results)
    return results


metadata = get_metadata()


setup(
    name=metadata['__title__'],
    version=metadata['__version__'],
    url=metadata['__url__'],
    license=metadata['__license__'],
    author=metadata['__author__'],
    author_email=metadata['__email__'],
    description=metadata['__summary__'],
    long_description=get_long_description(),

    packages=find_packages(),
    package_data={
        '': ['*.txt', '*.md', '*.rst']
    },
    include_package_data=True,
    keywords='graph vertex edge node link network semantic database',
    classifiers=[
        'Development Status :: 4 - Beta',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3 :: Only',
        'Topic :: Database :: Front-Ends',  # Graph databases, in particular
        'Topic :: Scientific/Engineering :: Information Analysis',
        'Topic :: Scientific/Engineering :: Interface Engine/Protocol Translator',
        'Topic :: Scientific/Engineering :: Mathematics',
    ]
)
