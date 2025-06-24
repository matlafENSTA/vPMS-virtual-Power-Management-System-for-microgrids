# -*- coding:utf-8 -*-
'''
:Created: 2025-06-19 10:18:30
:Project: virtual PMS for microgrids
:Version: 1.0
:Author: Mathieu Lafitte
:Description: Setup file for virtualPMS package. This file is used to install the package and its dependencies (no need to run it directly).
'''
#---------------------
#%%

# %%
import os
from setuptools import setup, find_packages

# Read dependencies from requirements.txt
with open(os.path.join(os.path.dirname(__file__), 'requirements.txt')) as f:
    requirements = f.readlines()

setup(
    name='virtualPMS',
    version='0.1.0',
    author='Mathieu LAFITTE',
    author_email='mathieu.lafitte@ensta.fr',
    description='A virtual Power Management System (PMS) module microgrids.',
    long_description=open(os.path.join(os.path.dirname(__file__), 'README.md')).read(),
    long_description_content_type='text/markdown',
    url='',
    packages=find_packages(include=['virtualPMS*']),
    include_package_data=True,
    install_requires=requirements,
    classifiers=[
        'Programming Language :: Python :: 3',
        'Operating System :: OS Independent',
    ],
    python_requires='>=3.7',
)

# %%
