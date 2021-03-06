"""Functions to make sure the specifications for a crawling/scraping are valid and work together correctly."""
from typing import List
import logging

from tld import get_tld

from scrawler.attributes import SearchAttributes, ExportAttributes, CrawlingAttributes


def validate_input_params(urls: List[str], search_attrs: SearchAttributes, export_attrs: ExportAttributes = None,
                          crawling_attrs: CrawlingAttributes = None, **kwargs):
    """Validate that all URLs work and the various attributes work together."""
    validate_urls(urls)

    if export_attrs is not None:
        # 1) Validate that n_filenames == n_URLs
        no_urls = len(urls)
        no_filenames = len(export_attrs.fn) if (type(export_attrs.fn) is list) else 1
        if not (no_urls == no_filenames):
            raise ValueError(f"Number of filenames ({no_urls}) provided is different that number of URLs to process ({no_filenames}).")

        # 2) Validate that header has same amount of columns as generated from search attributes (if passed as a list)
        header = export_attrs.header
        if header and (header != "first-row"):     # check that it's not None or False
            if not (len(header) == search_attrs.n_return_values):
                raise ValueError(f"Length of the header ({len(header)}) for exporting data is not equal to the"
                                 f" number of columns generated by the search attributes ({search_attrs.n_return_values})."
                                 f"\n\tHeader: {header}.")

    # 3) If using dynamic parameters, passed lists of parameters should have the same length as len(urls)
    for extractor in search_attrs.attributes:
        if extractor.dynamic_parameters:
            for param, value in extractor.__dict__.items():
                if type(value) is list:    # check only lists, not tuples or constants
                    if not len(value) == len(urls):
                        raise ValueError(f"You have passed a data extractor of class {extractor.__class__} using dynamic parameters."
                                         f" However, the number of parameters you passed for the attribute '{param}' does not equal the amount of URLs to be processed."
                                         f" You have to pass either a list of parameters of the same length as the number of URLs, or pass constants (not of type list).")


def validate_urls(urls: List[str]) -> None:
    """Checks if URL(s) can be parsed and checks for duplicates."""
    for url in urls:
        get_tld(url)

    # Check for duplicates by converting to set()
    if not len(urls) == len(set(urls)):
        logging.warning(f"The list of urls to process contains {len(urls) - len(set(urls))} duplicate(s).")
