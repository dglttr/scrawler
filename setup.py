from setuptools import setup, find_packages

try:
    with open("README.md") as f:
        readme = f.read()
except IOError:
    readme = ""

setup(
    name='scrawler',
    version='0.2.0',
    packages=find_packages(),
    url='https://github.com/dglttr/scrawler',
    author='Daniel Glatter',
    author_email='d.glatter@outlook.com',
    description='Tool for General Purpose Web Scraping and Crawling',
    long_description=readme,
    long_description_content_type="text/markdown",
    license="MIT",
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.6",
    keywords='Web Scraping, Crawling, asyncio, multithreading',
    install_requires=['beautifulsoup4>=4.9.1',
                      'requests>=2.24.0',
                      'tld>=0.12.5',
                      'pandas>=1.0.5',
                      'python-dateutil>=2.8.1',
                      'setuptools>=28.8.0',
                      'aiohttp>=3.7.3',
                      'readability-lxml >= 0.8.1']
)
