from setuptools import setup

gs = {}
ls = {}

with open('pykedixa/version.py') as f:
    exec(f.read(), gs, ls)

setup(
    name='kedixa',
    version=ls['__version__'],
    author='kedixa',
    description='kedixa\'s personal python toy library',
    url='https://github.com/kedixa/pykedixa/',
    packages=['kedixa', 'kedixa.comm'],
    package_dir={
        'kedixa.comm': 'pykedixa/comm',
        'kedixa': 'pykedixa',
    },
    install_requires=[],
    python_requires='>=3.6'
)
