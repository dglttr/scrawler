Welcome to scrawler's documentation!
====================================

*"scrawler" = "scraper" + "crawler"*

Provides functionality for the automatic collection of website data
(`web scraping <https://en.wikipedia.org/wiki/Web_scraping>`__) and
following links to map an entire domain
(`crawling <https://en.wikipedia.org/wiki/Web_crawler>`__). It can
handle these tasks individually, or process several websites/domains in
parallel using ``asyncio`` and ``multithreading``.

This project was initially developed while working at the `Fraunhofer
Institute for Systems and Innovation
Research <https://www.isi.fraunhofer.de/en.html>`__. Many thanks for the
opportunity and support!

Installation
------------

You can install scrawler from PyPI:

::

    pip install scrawler

.. note::
    Alternatively, you can find the ``.whl`` and ``.tar.gz`` files on GitHub
    for each respective `release <https://github.com/dglttr/scrawler/releases>`__.

Getting Started
---------------

Check out the `Getting Started Guide <getting_started.html>`__.

Important concepts and classes
------------------------------

Website Object
~~~~~~~~~~~~~~
Basic object to contain information on one website. This is basically a wrapper around a
`BeautifulSoup <https://www.crummy.com/software/BeautifulSoup/bs4/doc/>`__ object constructed from a website's HTML text,
adding additional information such as the URL and `its parts <reference.html#scrawler.utils.web_utils.ParsedUrl>`__ and the HTTP response when fetching the website.

- `Website Object documentation <reference.html#scrawler.website.Website>`__

Crawling/Scraping attribute objects
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Used for specifying options for the crawling/scraping processes, like what data to collect, which URLs to include and where to save the data.

- :class:`.SearchAttributes`: Specify which data to collect/search for in the website (and how to do it)
- :class:`.ExportAttributes`: Specify how and where to export the collected data to
- :class:`.CrawlingAttributes`: Specify how to conduct the crawling, e.g. how to filter irrelevant URLs or limits on the number of URLs crawled. As implied by their name, they are only relevant for crawling tasks.


Data Extractors
~~~~~~~~~~~~~~~
Data extractors are functions used to retrieve various data points from :class:`.Website` objects.

- `List of built-in data extractors <built_in_data_extractors.html>`__
- `Guide on how to build custom data extractors <custom_data_extractors.html>`__


.. toctree::
   :hidden:

   getting_started
   built_in_data_extractors
   custom_data_extractors
   reference


Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`

