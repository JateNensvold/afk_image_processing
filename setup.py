from setuptools import setup

with open("README.md", 'r') as f:
    long_description = f.read()

setup(
    name='afk-processing',
    version='1.0',
    description='A module for processing afk arena screenshots into '
    'textual information',
    license="MIT",
    long_description=long_description,
    author='Nate Jensvold',
    author_email='jensvoldnate@gmail.com',
    # url="http://www.foopackage.com/",
    packages=['image_processing'],  # same as name
    # external packages as dependencies
    install_requires=['wheel', 'bar'],
    scripts=[

    ]
)
