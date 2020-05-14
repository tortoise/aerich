import os
import re
from setuptools import find_packages, setup


def version():
    ver_str_line = open('alice/__init__.py', 'rt').read()
    mob = re.search(r"^__version__ = ['\"]([^'\"]*)['\"]", ver_str_line, re.M)
    if not mob:
        raise RuntimeError("Unable to find version string")
    return mob.group(1)


with open(os.path.join(os.path.dirname(__file__), 'README.rst')) as f:
    long_description = f.read()


def requirements():
    return open('requirements.txt', 'rt').read().splitlines()


setup(
    name='alice',
    version=version(),
    description='A database migrations tool for Tortoise-ORM.',
    author='long2ice',
    long_description_content_type='text/x-rst',
    long_description=long_description,
    author_email='long2ice@gmail.com',
    url='https://github.com/long2ice/alice',
    license='MIT License',
    packages=find_packages(include=['alice*']),
    include_package_data=True,
    zip_safe=True,
    entry_points={
        'console_scripts': ['alice = alice.cli:main'],
    },
    platforms='any',
    keywords=(
        'migrations Tortoise-ORM mysql'
    ),
    install_requires=requirements(),
)
