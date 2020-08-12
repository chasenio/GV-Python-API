from setuptools import setup, find_packages

"""
...
"""

install_requires = [
    'selenium==3.8.0',
    'urllib3>=1.23',
    'requests>=2.18.1',
    'beautifulsoup4==4.6.0',
]


setup(
    name='gvapi',
    version='0.0.1',
    author='kentio',
    author_email='13550898+kentio@users.noreply.github.com',
    url='https://github.com/kentio',
    packages=find_packages(exclude=('tests',)),
    license='LICENSE',
    description='Google Voice Python API',
    long_description=__doc__,
    zip_safe=False,
    install_requires=install_requires,
)
