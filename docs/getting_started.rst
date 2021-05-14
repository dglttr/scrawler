Getting Started
===============

To get started, have a look at the `templates <https://github.com/dglttr/scrawler/tree/main/templates>`__ folder. It
contains four files, each one doing a different task. All templates include three sections:

1. **Imports** retrieves all code dependencies from various files.
2. **Setup** is where all parameters are specified.
3. In **Execution**, an instance of the respective Python object is created and its ``run()`` method executed.

As a starting point, you can copy-and-paste a template and make any adjustments you would like.

Let's have a closer look at the **Setup** section.

First, the *URL(s)* to be processed are specified.

Then, the *attributes* that define how to accomplish the tasks are specified:

.. autosummary::
   :nosignatures:

   ~scrawler.attributes.SearchAttributes
   ~scrawler.attributes.ExportAttributes
   ~scrawler.attributes.CrawlingAttributes

For more details, see the section `Attributes`_.

In the section **Execution**, these parameters are then passed to the relevant object (see next section).

Basic Objects
-------------

The basic functionality of **scrawler** is contained in two classes, :class:`.Scraper` and :class:`.Crawler`.

Functionality
~~~~~~~~~~~~~

The objects are passed all relevant parameters during object initialization.
Then, three methods can be applied to them:

-  ``run()``: Execute the task and return the results.
-  ``run_and_export()``: This may be used when scraping/crawling many
   sites at once, generating huge amounts of data. In order to prevent a
   ``MemoryError``, data will be exported as soon as it is ready and
   then discarded to make room for the next sites/domains.
-  ``export_data()``: Export the collected data to CSV file(s).

Example Crawling
~~~~~~~~~~~~~~~~

Let's have a look at an example for **crawling** ``https://example.com``.
For the moment, you can ignore the variables ``search_attrs``, ``export_attrs`` and ``crawling_attrs``.
We will get to them `later <#attributes>`_.

.. code:: python

   from scrawler import Crawler

   search_attrs, export_attrs, crawling_attrs = ..., ..., ...

   crawler = Crawler("https://example.com",
                     search_attributes=search_attrs,
                     export_attributes=export_attrs,
                     crawling_attributes=crawling_attrs)
   results = crawler.run()
   crawler.export_data()

Example Scraping
~~~~~~~~~~~~~~~~

Here, multiple sites are **scraped** at once.

.. code:: python

   from scrawler import Scraper

   search_attrs, export_attrs = ..., ...

   scraper = Scraper(["https://www.example1.com", "https://www.example2.com", "https://www.example3.com"],
                     search_attributes=search_attrs,
                     export_attributes=export_attrs)
   results = scraper.run()
   scraper.export_data()

Attributes
----------

Now that we know the objects that will perform our tasks, we would like to specify exactly how to go about it.

Search Attributes
~~~~~~~~~~~~~~~~~

The :class:`.SearchAttributes` specify which data to collect/search for in
the website (and how to do it). This is done by passing data extractor
objects to :class:`.SearchAttributes` during initialization.

There are many data extractors already build into the project, see `built-in data extractors <built_in_data_extractors.html>`__.
You can also specify your own `custom data extractors <custom_data_extractors.html>`__.

In this example, we set up :class:`.SearchAttributes` that will extract three different data points from websites,
specified using the built-in :class:`.UrlExtractor`, :class:`.TitleExtractor` and :class:`.DateExtractor` data extractors.
Note how parameters for the data extractors are passed directly during initialization.

.. code:: python

   from scrawler.attributes import SearchAttributes
   from scrawler.data_extractors import *

   search_attrs = SearchAttributes(
       UrlExtractor(),  # returns URL
       TitleExtractor(),  # returns website <title> tag content
       DateExtractor(tag_types="meta", tag_attrs={"name": "pubdate"})  # returns publication date from pubdate meta tag
   )

.. seealso:: :class:`.SearchAttributes`: More detailed documentation.

Export Attributes
~~~~~~~~~~~~~~~~~

The :class:`.ExportAttributes` specify how and where to export the collected
data to. Data is always exported to the CSV format, therefore the
various parameters are geared towards the CSV format.

Two parameters *must* be specified here:

-  ``directory``: The directory (folder) that the file(s) will be saved to.
-  ``fn``: Filename(s) of the exported CSV files containing the crawled data.
   You don't have to specify the file extension ``.csv``, since the files will always be CSV files
   (for example, use ``crawled_data`` instead of ``crawled_data.csv``).

Here's an exemplary :class:`.ExportAttributes` object creation:

.. code:: python

   from scrawler.attributes import ExportAttributes

   export_attrs = ExportAttributes(
       directory=r"C:\Users\USER\Documents",
       fn=["example1_crawled_data", "example1_crawled_data", "example1_crawled_data"],
       header=["URL", "Title", "Publication Date"],
       separator="\t"
   )

.. seealso:: :class:`.ExportAttributes`: More detailed documentation.

Crawling Attributes
~~~~~~~~~~~~~~~~~~~

The :class:`.CrawlingAttributes` specify how to conduct the crawling, e.g.
how to filter irrelevant URLs or limits on the number of URLs crawled.
As implied by their name, they are only relevant for crawling tasks.

Some commonly adjusted parameters include:

-  ``filter_foreign_urls``: This parameter defines how the crawler knows
   that a given URL is still part of the target domain. For example, one
   may only want to crawl a subdomain, not the entire domain (only URLs
   from ``subdomain.example.com`` vs. the entire ``example.com``
   domain). Details on valid input values can be found in the
   documentation for :class:`.CrawlingAttributes`. By default,
   this is set to ``auto``, which means that the correct mode will be
   inferred by looking at the passed base/start URL. For example, if the
   start URL contains a subdomain, only links from the subdomain will be
   crawled. For details, refer to the documentation for the
   :func:`.extract_same_host_pattern` function. Note that you can also pass
   your own comparison function here. It has to include two parameters,
   ``url1`` and ``url2``. The first URL is the one to be checked, and
   the second is the reference (the crawling start URL). This function
   should return ``True`` for URLs that belong to the same host, and
   ``False`` for foreign URLs.
-  ``filter_media_files``: Controls whether to filter out (ignore) media
   files. Media files can be quite large and make the crawling process
   significantly longer, while not adding any new information because
   media file data can't be parsed and processed. Therefore, the crawler
   filters media by looking at the URL (e.g. URLs ending in ``.pdf`` or
   ``.jpg``), as well as the response header
   `content-type <https://developer.mozilla.org/en-US/docs/Web/HTTP/Headers/Content-Type>`__.
-  ``blocklist``: Some directories might not be interesting for the
   crawling process (e.g., ``/media/``). The ``blocklist`` parameter
   makes it possible to pass a list of strings that might occur in a
   URL. If the URL contains any of the given strings, it is filtered
   out.
-  ``max_no_urls``: Some domains contain many webpages. This parameter
   can be passed an integer as the maximum total amount of URLs to be
   crawled.

Here's an exemplary :class:`.CrawlingAttributes` object creation:

.. code:: python

   from scrawler.attributes import CrawlingAttributes

   DOMAIN_TO_CRAWL = "https://www.blog.example.com"

   crawling_attrs = CrawlingAttributes(
       filter_foreign_urls="subdomain1",  # only crawling the `blog` subdomain
       filter_media_files=True,
       blocklist=("git.", "datasets.", "nextcloud."),
       max_no_urls=1000
   )

Another example with a custom foreign URL filter:

.. code:: python

   import tld.exceptions

   from scrawler.attributes import CrawlingAttributes
   from scrawler.utils.web_utils import ParsedUrl

   DOMAIN_TO_CRAWL = "https://www.blog.example.com/my_directory/index.html"


   def should_be_crawled(url1: str, url2: str) -> bool:
       """Custom foreign URL filter: Crawl all URLs from host `www.blog.example.com` inside the directory `my_directory`."""
       try:  # don't forget exception handling
           url1 = ParsedUrl(url1)
           url2 = ParsedUrl(url2)
       except (tld.exceptions.TldBadUrl, tld.exceptions.TldDomainNotFound):  # URL couldn't be parsed
           return False

       return ((url1.hostname == url2.hostname)  # hostname is `www.blog.example.com`
               and ("my_directory" in url1.path) and ("my_directory" in url2.path))


   crawling_attrs = CrawlingAttributes(
       filter_foreign_urls=should_be_crawled,  # pass custom foreign URL filter here
       filter_media_files=True,
       blocklist=("git.", "datasets.", "nextcloud."),
       max_no_urls=1000
   )

.. seealso:: :class:`.CrawlingAttributes`: More detailed documentation.

Other Settings
~~~~~~~~~~~~~~

Most parameters are encompassed in the three attribute objects above.
However, there are some additional settings available for special cases.

If you look at the templates' **Setup** section again, it includes a ``USER_AGENT`` parameter that sets the
`user agent <https://en.wikipedia.org/wiki/User_agent>`__ to be used during scraping/crawling.

Finally, `defaults.py <https://github.com/dglttr/scrawler/blob/main/scrawler/defaults.py>`__
contains standard settings that are used throughout the project.

FAQ
---

Why are there two backends?
~~~~~~~~~~~~~~~~~~~~~~~~~~~

The module `backends <https://github.com/dglttr/scrawler/tree/main/scrawler/backends>`__ contains two files with
the same functions for scraping and crawling, but built on different
technologies for parallelization. In general, the ``asyncio`` version is
preferable because more sites can be processed in parallel. However, on
very large sites, scrawler may get stuck, and the entire crawling will
hang. Also, there you may occasionally get many
``ServerDisconnectedError``\ s when using the ``asyncio`` backend. If
you expect or experience these cases, it is preferable to use the
backend built on ``multithreading``, which is slower, but more robust.

- `asyncio Backend Documentation <reference.html#module-scrawler.backends.asyncio_backend>`__
- `multithreading Backend Documentation <reference.html#module-scrawler.backends.multithreading_backend>`__
