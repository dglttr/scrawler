"""Specifies the attribute objects used by crawlers and scrapers."""
from typing import Tuple, Union, Callable
from inspect import signature
import os

import pandas as pd

from scrawler.defaults import (DEFAULT_CSV_ENCODING, DEFAULT_CSV_SEPARATOR, DEFAULT_CSV_QUOTING, DEFAULT_CSV_ESCAPECHAR,
                               DEFAULT_PAUSE_TIME)
from scrawler.website import Website
from scrawler.data_extractors import BaseExtractor
from scrawler.utils.web_utils import is_same_host, extract_same_host_pattern


class SearchAttributes:
    def __init__(self, *args: BaseExtractor, validate: bool = True):
        """Specify which data to collect/search for in the website.

        :param args: Data extractors specifying which data to extract in websites
            (see `built-in data extractors <built_in_data_extractors.html>`__  or for possibilities
            or `define a custom data extractor <custom_data_extractors.html>`__).
        :param validate: Whether to make sure that input parameters are valid.
        """
        if validate:
            for extractor in args:
                if not isinstance(extractor, BaseExtractor):
                    raise TypeError(f"{extractor.__class__} does not inherit from BaseExtractor.")

        self.attributes: Tuple[BaseExtractor] = args
        self.n_return_values: int = sum([extractor.n_return_values for extractor in self.attributes])

    def extract_all_attrs_from_website(self, website: Website, index: int = None) -> list:
        """Extract data from a website using data extractors specified in ``SearchAttributes`` definition.

        :param website: Website object to collect the specified data points from.
        :param index: Optionally pass an index for data extractors that index into passed parameters.
            See `this explanation <custom_data_extractors.html#dynamic-parameters>`__ for details.
        """
        extracted_data = []

        for extractor in self.attributes:
            # Case handling for functions using an index
            if (index is not None) and extractor.dynamic_parameters:
                result = extractor.run(website, index)
            else:
                result = extractor.run(website)

            # Case handling for functions with multiple return values
            if extractor.n_return_values != 1:
                extracted_data.extend(result)
            else:
                extracted_data.append(result)

        return extracted_data


class ExportAttributes:
    def __init__(self, directory: str, fn: Union[str, list],
                 header: Union[list, str, bool] = None, encoding: str = DEFAULT_CSV_ENCODING,
                 separator: str = DEFAULT_CSV_SEPARATOR, quoting: int = DEFAULT_CSV_QUOTING,
                 escapechar: str = DEFAULT_CSV_ESCAPECHAR, validate: bool = True, **kwargs):
        """Specify how and where to export the collected data.

        :param directory: Folder where file(s) will be saved to.
        :param fn: Name(s) of the file(s) containing the crawled data. *Without* file extension.
        :param header: Have the final CSV file have a header. Possible parameters:
            If ``None`` or ``False``, no header will be written.
            If ``first-row`` or ``True``, uses first row of data as header.
            Else, pass list of strings of appropriate length.
        :param encoding: Encoding to use to create the CSV file.
        :param separator: Column separator or delimiter to use for creating the CSV file.
        :param quoting: Puts quotes around cells that contain the separator character.
        :param escapechar: Escapes the separator character.
        :param validate: Whether to make sure that input parameters are valid.
        :param kwargs: Any parameter supported by :meth:`pandas:pandas.DataFrame.to_csv` can be passed.
        """
        if validate:
            # Check that directory exists
            if not os.path.isdir(directory):
                raise NotADirectoryError(f"Export directory does not exist on this system ({directory}).")

            # Check that keyword arguments are allowed for pandas.DataFrame.to_csv()
            for key, value in kwargs.items():
                if key not in signature(pd.DataFrame.to_csv).parameters:
                    raise ValueError(f'Invalid keyword argument passed to ExportAttributes: "{key}"')

        self.directory = directory
        self.fn = fn    # Filename(s)

        self.header = header
        self.encoding = encoding
        self.separator = separator
        self.quoting = quoting
        self.escapechar = escapechar

        for key, value in kwargs.items():   # Add keyword arguments as attributes
            self.__setattr__(key, value)


class CrawlingAttributes:
    def __init__(self,
                 filter_non_standard_schemes: bool = True,
                 filter_media_files: bool = True,
                 blocklist: tuple = (),
                 filter_foreign_urls: Union[str, Callable] = "auto",
                 strip_url_parameters: bool = False,
                 strip_url_fragments: bool = True,

                 max_no_urls: int = None,
                 max_distance_from_start_url: int = None,
                 max_subdirectory_depth: int = None,

                 pause_time: float = DEFAULT_PAUSE_TIME,
                 respect_robots_txt: bool = True,

                 validate: bool = True
                 ):
        """Specify how to conduct the crawling, including filtering irrelevant URLs or limiting the number of crawled URLs.

        :param filter_non_standard_schemes: Filter URLs starting with schemes other than ``http:`` or ``https:`` (e.g., ``mailto:`` or ``javascript:``).
        :param filter_media_files: Whether to filter media files. Recommended: ``True`` to avoid long runtimes caused by large file downloads.
        :param blocklist: Filter URLs that contain one or more of the parts specified here. Has to be a ``list``.
        :param filter_foreign_urls: Filter URLs that do not belong to the same host (foreign URLs).
            Can either be a string that is passed to :func:`.is_same_host`, or a custom ``Callable`` that has to include two arguments, ``url1`` and ``url2``.
            In :func:`.is_same_host`, the following string values are permitted:
            1. ``auto``: Automatically extracts a matching pattern from the start URL (see :func:`.extract_same_host_pattern` for details).
            2. Any one of the attributes of the :class:`.ParsedUrl` class (e.g. ``domain``, ``hostname``, ``fld``).
            3. ``subdomainX`` with ``X`` representing an integer number up to which subdomain the URLs should be compared. E.g., comparing ``http://www.sub.example.com`` and ``http://blog.sub.example.com``, ``sub`` is the first level, while the second levels are ``www`` and ``blog``, respectively.
            4. ``directoryX`` with ``X`` representing an integer number up to which directory the URLs should be compared. E.g., for ``http://example.com/dir1/dir2/index.html``, ``directory2`` would include all files in ``dir2``.

        :param strip_url_parameters: Whether to strip URL query parameters (prefixed by ``?``) from the URL.
        :param strip_url_fragments: Whether to strip URL fragments (prefixed by ``#``) from the URL.

        :param max_no_urls: Maximum number of URLs to be crawled per domain (safety limit for very large crawls). Set to ``None`` if you want all URLs to be crawled.
        :param max_distance_from_start_url: Maximum number of links that have to be followed to arrive at a certain URL from the start URL.
        :param max_subdirectory_depth: Maximum sub-level of the host up to which to crawl. E.g., consider this schema: ``hostname/sub-directory1/sub-siteA``.
            If you would want to crawl all URLs of the same level as ``sub-directory1``, specify 1.
            ``sub-siteA`` will then not be found, but a site ``hostname/sub-directory2`` or ``hostname/sub-siteB`` will be.

        :param pause_time: Time to wait between the crawling of two URLs (in seconds).
        :param respect_robots_txt: Whether to respect the specifications made in the website's ``robots.txt`` file.
        """
        if validate:
            # Check that a valid input is passed to parameter filter_foreign_url
            TEST_URL = "https://www.example.com"
            try:
                if not isinstance(filter_foreign_urls, Callable):
                    test_mode = extract_same_host_pattern(TEST_URL) if (filter_foreign_urls == "auto") else filter_foreign_urls
                    assert is_same_host(TEST_URL, TEST_URL, mode=test_mode), "is_same_host() should be True if the same URL is used."
                else:
                    assert filter_foreign_urls(TEST_URL, TEST_URL), f"Error when testing your custom foreign URL filter function ({filter_foreign_urls.__name__}): Should be True if the same URL is used for both input arguments."
            except (ValueError, TypeError, AssertionError) as e:
                raise ValueError(f"Parameter filter_foreign_url is not correctly specified: {filter_foreign_urls}. The following error occurred during validation: {e}")

        self.filter_non_standard_schemes = filter_non_standard_schemes
        self.filter_media = filter_media_files
        self.blocklist = blocklist
        self.filter_foreign_urls = filter_foreign_urls
        self.strip_url_parameters = strip_url_parameters
        self.strip_url_fragments = strip_url_fragments

        self.max_no_urls = max_no_urls if (max_no_urls is not None) else float("inf")
        self.max_distance_from_start_url = max_distance_from_start_url if (max_distance_from_start_url is not None) else float("inf")
        self.max_subdirectory_depth = max_subdirectory_depth if (max_subdirectory_depth is not None) else float("inf")

        self.pause_time = pause_time
        self.respect_robots_txt = respect_robots_txt
