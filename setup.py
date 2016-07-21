from setuptools import setup

setup(
    name='kbharvester',
    version='0.2.0',
    packages=['nl', 'nl.leidenuniv', 'nl.leidenuniv.library', 'nl.leidenuniv.library.harvester'],
    url='https://github.com/bencomp/KB-harvester',
    license='GPL',
    author='Ben Companjen',
    author_email='b.a.companjen@library.leidenuniv.nl',
    description='A wrapper for KB data access APIs',
    install_requires=['requests','kb']
)
