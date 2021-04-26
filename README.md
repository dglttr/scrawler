# scrawler
_"scrawler" = "scraper" + "crawler"_

Provides functionality for the automatic collection of website data ([web scraping](https://en.wikipedia.org/wiki/Web_scraping))
and following links to map an entire domain ([crawling](https://en.wikipedia.org/wiki/Web_crawler)).
It can handle these tasks individually, or process several websites/domains in parallel using `asyncio` and `multithreading`.

This project was initially developed while working at the [Fraunhofer Institute for Systems and Innovation Research](https://www.isi.fraunhofer.de/en.html). Many thanks for the opportunity and support!

## Table of Contents
  <ol>
    <li><a href="#getting-started">Getting Started</a></li>
    <li><a href="#basic-objects">Basic Objects</a></li>
    <li>
        <a href="#attributes">Attributes</a>
        <ul>
            <li><a href="#search-attributes">Search Attributes</a></li>
            <li><a href="#export-attributes">Export Attributes</a></li>
            <li><a href="#crawling-attributes">Crawling Attributes</a></li>
            <li><a href="#other-settings">Other Settings</a></li>
        </ul>
    </li>
    <li><a href="#faq">FAQ</a></li>
  </ol>

## Getting Started
You can install scrawler from PyPI:
```
pip install scrawler
```

Alternatively, you can find the `.whl` and `.tar.gz` files on GitHub for each respective [release](https://github.com/dglttr/scrawler/releases).

To start, have a look at the [`templates`](templates) folder. It contains four files, each one doing a different task.
All template include three sections: Imports, Setup and Execution.
- **Imports** retrieves all code dependencies from various files
- **Setup** is where all parameters are specified
- In **Execution**, an instance of the respective Python object is created and its `run()` method executed

You can copy-and-paste the template and make any adjustments you would like. Make sure to paste it within the project directory.

### Specifying parameters
Let's have a closer look at the "setup" section.

First, the **URLs** that are to be processed are specified (for more details, have a look at the section <a href="#attributes">Attributes</a>).

Then, the attributes that define how to accomplish the tasks are specified:
- The **search attributes** specify which data to collect/search for in the website (and how to do it)
- The **export attributes** specify how and where to export the collected data to
- In the case of a crawling task, the **crawling attributes** specify how to conduct the crawling, e.g. how to filter irrelevant URLs or limits on the number of URLs crawled.

In the section "execution", these parameters are then passed to the relevant object (see section <a href="#basic-objects">Basic Objects</a>).

## Basic Objects
The basic functionality of **scrawler** is contained in two classes, [`scraping`](scrawler/scraping.py).`Scraper` and [`crawling`](scrawler/crawling.py).`Crawler`.

### Functionality
The objects are passed all relevant parameters during object initialization
and then executed by calling the object's `run()` or `run_and_export()` methods.
Afterwards, data may be exported by calling the `export_data()` method.

To sum it up:
- `run()`: Execute the task and return the results.
- `run_and_export()`: This may be used when scraping/crawling many sites at once, generating huge amounts of data.
    In order to prevent a `MemoryError`, data will be exported as soon as it is ready and then discarded to make room for the next sites/domains.
- `export_data()`: Export the collected data to CSV file(s).

### Example Crawling
Let's have a look at an example. For more information on how to create search, export and crawling attributes, you can refer to the section <a href="#attributes">Attributes</a>:
```python
from scrawler import Crawler

search_attrs, export_attrs, crawling_attrs = ..., ..., ...

crawler = Crawler("https://example.com",
                  search_attributes=search_attrs,
                  export_attributes=export_attrs,
                  crawling_attributes=crawling_attrs)
results = crawler.run()
crawler.export_data()
```

### Example Scraping
Here, multiple sites are scraped at once.
```python
from scrawler import Scraper

search_attrs, export_attrs = ..., ...

scraper = Scraper(["https://www.example1.com", "https://www.example2.com", "https://www.example3.com"],
                  search_attributes=search_attrs,
                  export_attributes=export_attrs)
results = scraper.run()
scraper.export_data()
```

## Attributes
Now that the object necessary for our task has been created, we would like to specify exactly how to go about the task.

### Search Attributes
The **search attributes** specify which data to collect/search for in the website (and how to do it).
This is done by passing data extractor objects to the `SearchAttributes` during initialization.

There are many data extractors already build into the project. For example, this example uses the built-in `DateExtractor` to extract a website's publication date from an [HTML meta tag](https://www.w3schools.com/tags/tag_meta.asp).

```python
from scrawler.data_extractors import DateExtractor

pubdate_extractor = DateExtractor(tag_types="meta", tag_attrs={"name": "pubdate"})
```

Have a look at `scrawler` > [`data_extractors.py`](scrawler/data_extractors.py) to see all available built-in data extractors.

Here's an exemplary `SearchAttributes` object creation:

```python
from scrawler.attributes import SearchAttributes
from scrawler.data_extractors import *

search_attrs = SearchAttributes(
    UrlExtractor(),  # returns URL
    TitleExtractor(),  # returns website <title> tag content
    DateExtractor(tag_types="meta", tag_attrs={"name": "pubdate"})  # returns publication date
)
```

Note how parameters for the data extractors are passed directly during initialization.

#### Custom data extractors
If you do not find what you need, you can also built a data extractor yourself.

Data extractors are passed a `Website` object, which provides access to three types of data:
- The website's HTML parsed as a BeautifulSoup object (see [their documentation](https://www.crummy.com/software/BeautifulSoup/bs4/doc/) for how to extract data from it).
  Because `Website` extends `BeautifulSoup`, you can directly execute BeautifulSoup methods on the website object.
- The HTTP response object (`http_response` attribute). This is an aiohttp [`ClientResponse`](https://docs.aiohttp.org/en/v3.7.3/client_reference.html#aiohttp.ClientResponse) object.
- The website's raw URL (`url` attribute) and parsed URL (`parsed_url` attribute) parts.

Data extractors must inherit from `BaseExtractor` and implement two methods:
- `__init__()`: Where parameters to the extractor can be passed and are stored in object attributes.
- `run()`: To do the extraction. Make sure that the method signature is the same as for `BaseExtractor`, i.e. two parameters can be passed, `website` and `index`as an optional parameter.

In this example, we build a data extractor to retrieve a website's copyright tag (if available):

```python
from scrawler import Website
from scrawler.data_extractors import BaseExtractor


class CopyrightExtractor(BaseExtractor):
    def __init__(self, **kwargs):
        """Extract website copyright tag."""
        super().__init__(**kwargs)

    def run(self, website: Website, index: int = None):
        copyright_tag = website.find("meta", attrs={"name": "copyright"})

        # Important: Do not forget to handle exceptions, because many sites will not have this copyright tag
        try:
            copyright_text = copyright_tag.attrs["content"]
        except (AttributeError, KeyError):
            copyright_text = "NULL"

        return copyright_text
```

In this case, we could actually have had an easier solution. The built-in extractor `GeneralHtmlTagExtractor` already contains all the necessary functionality:

```python
from scrawler.data_extractors import GeneralHtmlTagExtractor

copyright_extractor = GeneralHtmlTagExtractor(tag_types="meta", tag_attrs={"name": "copyright"},
                                              attr_to_extract="content")
```

#### Special parameters
Some notes on basic parameters specified in `BaseExtractor` that apply to all data extractors.

The parameter **`n_return_values`** specifies the number of values that will be returned by the extractor.
This is almost always 1, but there are cases such as `DateExtractor` which may return more values.
If you build your own data extractor that may return more than one value, make sure to update `self.n_return_values`.
This attribute is used to validate that the length of the header of the CSV file equals the number of columns generated by the search attributes.
Have a look at the implementation of `DateExtractor` to see how this might be handled.

The parameter **`dynamic_parameters`** handles a special case of data extraction when scraping/crawling multiple sites.
There may be cases where you would like to have a different set of parameters for each URL.
In this case, you can pass the relevant parameter as a list and set `dynamic_parameters` to True.
The scraper/crawler will then have each URL/scraping target use a different value from that list based on an index.
In this example, a different ID will be put for each crawled domain:

```python
from scrawler.data_extractors import CustomStringPutter

DOMAINS_TO_CRAWL = ["https://www.abc.com", "https://www.def.com", "https://www.ghi.com"]
putter = CustomStringPutter(["id_1001", "id_1002", "id_1003"], use_index=True)
```
Note that when enabling `dynamic_parameters`, to parameters going into this data extractor can only have one of two forms:
- A list (not a tuple!) where each list entry matches _exactly one_ URL (in the same order as in the list of the URLs, see variable `DOMAINS_TO_CRAWL` in the example above).
- A constant (of a type other than list) than will be the same for all URLs.

Passing a parameter list shorter or longer than the list of URLs will raise an error.

All built-in data extractors support dynamic parameters and you can easily add support to your custom data extractor
by using the `supports_dynamic_parameters` function decorator to decorate the `run()` method, like this:

```python
from scrawler import Website
from scrawler.data_extractors import BaseExtractor, supports_dynamic_parameters


class CopyrightExtractor(BaseExtractor):
    def __init__(self, **kwargs):
        """Extract website copyright tag."""
        super().__init__(**kwargs)

    @supports_dynamic_parameters
    def run(self, website: Website, index: int = None):
        copyright_tag = website.find("meta", attrs={"name": "copyright"})

        # Important: Do not forget to handle exceptions, because many sites will not have this copyright tag
        try:
            copyright_text = copyright_tag.attrs["content"]
        except (AttributeError, KeyError):
            copyright_text = "NULL"

        return copyright_text
```

### Export Attributes
The **export attributes** specify how and where to export the collected data to.
Data is always exported to the CSV format, therefore the various parameters are geared towards the CSV format.

Two parameters _must_ be specified here:
- `directory`: The directory (folder) that the file(s) will be saved to.
- `fn`: (filename/filenames) Name(s) of the file(s) containing the crawled data, without the file extension. For example, `crawled_data` instead of `crawled_data.csv`.

Refer to the object's documentation in the code at `scrawler` > [`attributes.py`](scrawler/attributes.py) for more information on other possible parameters.

Here's an exemplary `ExportAttributes` object creation:

```python
from scrawler.attributes import ExportAttributes

export_attrs = ExportAttributes(
    directory=r"C:\Users\USER\Documents",
    fn=["crawled_data_abc", "crawled_data_def", "crawled_data_ghi"],
    header=["URL", "Title", "Publication Date"],
    separator="\t"
)
```

### Crawling Attributes
The **crawling attributes** specify how to conduct the crawling, e.g. how to filter irrelevant URLs or limits on the number of URLs crawled.
As implied by their name, they are only relevant for crawling tasks.
Some commonly adjusted parameters include:
- `filter_foreign_urls`: This parameter defines how the crawler knows that a given URL is still part of the target domain.
    For example, one may only want to crawl a subdomain, not the entire domain (only URLs from `subdomain.example.com` vs. the entire `example.com` domain).
    Details on valid input values can be found in the documentation for `CrawlingAttributes` in the code.
    Note that you can also pass your own comparison function here. It has to include two parameters, `url1` and `url2`.
    The first URL is the one to be checked, and the second is the reference (the crawling start URL).
    This function should return `True` for URLs that belong to the same host, and `False` for foreign URLs.
- `filter_media_files`: Controls whether to filter out (ignore) media files. Media files can be quite large and make the crawling process
    significantly longer, while not adding any new information because media file data can't be parsed and processed.
    Therefore, the crawler filters media by looking at the URL (e.g. URLs ending in `.pdf` or `.jpg`), as well as the response header [content-type](https://developer.mozilla.org/en-US/docs/Web/HTTP/Headers/Content-Type).
- `blocklist`: Some directories might not be interesting for the crawling process (e.g., `/media/`).
    The `blocklist` parameter makes it possible to pass a list of strings that might occur in a URL. If the URL contains any of the given strings, it is filtered out.
- `max_no_urls`: Some domains contain many webpages. This parameter can be passed an integer as the maximum total amount of URLs to be crawled.

Refer to the object's documentation in the code at `scrawler` > [`attributes.py`](scrawler/attributes.py) for more information on other possible parameters.

Here's an exemplary `CrawlingAttributes` object creation:

```python
from scrawler.attributes import CrawlingAttributes

DOMAIN_TO_CRAWL = "https://www.blog.example.com"

crawling_attrs = CrawlingAttributes(
    filter_foreign_urls="subdomain1",  # only crawling the `blog` subdomain
    filter_media_files=True,
    blocklist=("git.", "datasets.", "nextcloud."),
    max_no_urls=1000
)
```

Another example with a custom foreign URL filter:

```python
import tld.exceptions

from scrawler.attributes import CrawlingAttributes
from scrawler.utils.web_utils import ParsedUrl

DOMAIN_TO_CRAWL = "https://www.blog.example.com/my_directory/index.html"


def should_be_crawled(url1: str, url2: str) -> bool:  # Custom foreign URL filter
    try:  # don't forget exception handling
        url1 = ParsedUrl(url1)
        url2 = ParsedUrl(url2)
    except (tld.exceptions.TldBadUrl, tld.exceptions.TldDomainNotFound):  # URL couldn't be parsed
        return False

    return ((url1.hostname == url2.hostname)  # hostname "www.blog.example.com"
            and ("my_directory" in url1.path) and ("my_directory" in url2.path))


crawling_attrs = CrawlingAttributes(
    filter_foreign_urls=should_be_crawled,  # crawl URLs from host "www.blog.example.com" inside the directory "my_directory"
    filter_media_files=True,
    blocklist=("git.", "datasets.", "nextcloud."),
    max_no_urls=1000
)
```

### Other Settings
Most parameters are encompassed in the three attribute objects above. However, there are some additional settings available for special cases.

If you look at the templates' "setup" section again, it includes a `USER_AGENT` parameter that sets the [user agent](https://en.wikipedia.org/wiki/User_agent) to be used during scraping/crawling.

Finally, the file `scrawler` > [`defaults.py`](scrawler/defaults.py) contains standard settings that are used throughout the project.

## FAQ
### I receive a `ModuleNotFoundError` when running a scraping/crawling script from the command line.
The cause of this problem is described [here](https://www.reddit.com/r/learnpython/comments/729u0t/module_not_found_error_when_trying_to_run_from_cmd/).
To fix it:
1.	Inside the command line window, navigate to the root folder where the project is located (not to the sub-folder where the script is located). Note: The script should be located within the project.
2.	Run the command `python -m folder_name.script_name.py`. Note the parameter `-m`and the use of `folder_name.`.

### Why are there two backends?
The folder `backends` contains two files that contain very similar functions for scraping and crawling, but built on different technologies for parallelization.
In general, the `asyncio` version is to be preferred because more sites can be processes in parallel. However, with very large sites, this may get stuck and the entire crawling will hang.
In these cases, it is preferable to use the backend built on `multithreading`.