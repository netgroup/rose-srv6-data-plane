#!/usr/bin/python


import os
import setuptools


with open("README.md", "r") as fh:
    long_description = fh.read()


# Read dependencies from requirements.txt
proj_dir = os.path.dirname(os.path.realpath(__file__))
requirements_path = os.path.join(proj_dir, 'requirements.txt')
install_requires = []
if os.path.isfile(requirements_path):
    with open(requirements_path) as f:
        install_requires = f.read().splitlines()

packages = [
    'data_plane',
    'data_plane/twamp',
]

setuptools.setup(
    name="rose-srv6-data-plane",
    version="0.0.1",
    description="Collection of data-plane modules for a node",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/netgroup/rose-srv6-data-plane",
    packages=packages,
    install_requires=install_requires,
    classifiers=[
        'Programming Language :: Python :: 3',
        'License :: OSI Approved :: Apache Software License',
        'Operating System :: Linux',
        'Programming Language :: Python',
    ],
    python_requires='>=3.6'
)
