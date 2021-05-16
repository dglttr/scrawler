from datetime import datetime
from typing import Union, Tuple, List, Callable
import functools

import dateutil.parser
from bs4 import BeautifulSoup, Tag, NavigableString
import readability

from scrawler.utils.general_utils import sanitize_text
from scrawler.website import Website
from scrawler.utils.web_utils import get_directory_depth
from scrawler.defaults import DEFAULT_EMPTY_FIELD_STRING

__all__ = ["GeneralHtmlTagExtractor", "GeneralHttpHeaderFieldExtractor", "AccessTimeExtractor", "CmsExtractor",
           "ContactNameExtractor", "CustomStringPutter", "DateExtractor", "DescriptionExtractor",
           "DirectoryDepthExtractor", "ExpiryDateExtractor", "HttpStatusCodeExtractor",
           "KeywordsExtractor", "LanguageExtractor", "LastModifiedDateExtractor", "LinkExtractor",
           "ServerProductExtractor", "StepsFromStartPageExtractor", "MobileOptimizedExtractor",
           "TermOccurrenceExtractor", "TermOccurrenceCountExtractor", "TitleExtractor", "UrlExtractor",
           "UrlBranchNameExtractor", "UrlCategoryExtractor", "WebsiteTextExtractor"]

# CONSTANTS: Default HTML attributes to collect certain data points
_DEFAULT_CMS_TAG_TYPE = "meta"
_DEFAULT_CMS_ATTRS = {"name": ["generator", "Generator", "formatter", "Powered-By", "application-name"]}
_DEFAULT_CMS_KEYWORDS = {"WordPress": ["wp-content", "wp-includes", "wp-uploads"],
                         "TYPO3 CMS": ["typo3"],
                         "Wix.com": ["/wix-bolt/", "wixcode-worker.js", "wixstatic.com"],
                         "Shopify": ["cdn.shopify.com", "shopify.js", "/shopify/"]}

_DEFAULT_CONTACT_TAG_TYPES = ("div")
_DEFAULT_CONTACT_TAG_ATTRS = {"class": "employee_name"}

_DEFAULT_DATE_TAG_TYPES = ("meta")
_DEFAULT_DATE_TAG_ATTRS = {"name": "pubdate"}

_DEFAULT_DESCRIPTION_TAG_TYPE = "meta"
_DESCRIPTION_TAG_ATTRS_1 = {"name": ["description", "Description"]}
_DESCRIPTION_TAG_ATTRS_2 = {"property": ["description", "Description", "og:description"]}

_DEFAULT_KEYWORDS_TAG_TYPE = "meta"
_DEFAULT_KEYWORDS_TAG_ATTRS = {"name": ["keywords", "Keywords"]}

_DEFAULT_TEXT_TAG_TYPES = ("div")
_DEFAULT_TEXT_TAG_ATTRS = {"class": ["content"]}
_DEFAULT_TEXT_ALLOWED_STRING_TYPES = [NavigableString]

_DEFAULT_IS_MOBILE_OPTIMIZED_TAG_TYPE = "meta"
_DEFAULT_IS_MOBILE_OPTIMIZED_TAG_ATTRS = {"name": "viewport"}


def supports_dynamic_parameters(func) -> Callable:
    """Function decorator to select correct parameter based on index when using dynamic parameters."""

    @functools.wraps(func)
    def run(self, website: Website, index: int = None) -> Callable:
        if index is not None and self.dynamic_parameters:
            # First, initialize new object to prevent changes to original.
            # Note that this has a high performance impact (though better than when using copy() or deepcopy())
            self_copy = self.__class__(**self.__dict__)

            for param, value in self_copy.__dict__.items():
                if type(value) is list:    # update only lists
                    self_copy.__dict__[param] = value[index]

            return func(self_copy, website, index)
        else:
            return func(self, website)

    return run


class BaseExtractor:
    def __init__(self, *args, dynamic_parameters: bool = False, n_return_values: int = None, **kwargs) -> None:
        """Provides the basic architecture for each data extractor.
        Every data extractor has to inherit from :class:`.BaseExtractor`.

        :param args: Positional arguments to be used by children inheriting from :class:`.BaseExtractor`.
        :param dynamic_parameters: Set this to ``True`` when you would like to pass a :class:`list` to a certain parameter,
            and have each URL/scraping target use a different value from that list based on an index.
            See also `here <custom_data_extractors.html#dynamic-parameters>`__.
        :param n_return_values: Specifies the number of values that will be returned by the extractor.
            This is almost always 1, but there are cases such as :class:`.DateExtractor` which may return more values.
            See also `here <custom_data_extractors.html#n-return-values>`__.
        :param kwargs: Keyword arguments to be used by children inheriting from :class:`.BaseExtractor`.
        """
        self.dynamic_parameters = dynamic_parameters
        self.n_return_values = n_return_values if (n_return_values is not None) else 1

    @supports_dynamic_parameters
    def run(self, website: Website, index: int = None):
        """Runs the extraction and returns the extracted data.

        :param website: :class:`.Website` object that data is extracted from.
        :param index: Used for extractors that should behave differently for each domain/site if multiple are processed.
            Usually, the extractor will be passed a list of values and use only the value relevant
            to the currently processed domain/site (for example, :class:`.CustomStringPutter` may put
            a different string for each domain). See also `here <custom_data_extractors.html#dynamic-parameters>`__.
        """
        pass


class GeneralHtmlTagExtractor(BaseExtractor):
    def __init__(self, tag_types: tuple, tag_attrs: dict, attr_to_extract: str,
                 fill_empty_field: bool = True, **kwargs):
        """General purpose extractor for extracting HTML tags and then extracting a single attribute from the tag.

        :param tag_types: Describes the tag types to find, e. g. ``div``.
        :param tag_attrs: Specifies the HTML attributes use to find the relevant HTML tag in a key-value dict format.
            Example: ``{"class": ["content", "main-content"]}``.
            See also `this explanation of HTML tag attributes <https://www.w3schools.com/htmL/html_attributes.asp>`__.
        :param attr_to_extract: The attribute that should be extracted from the found HTML tag.
        :param fill_empty_field: Used in cases where the specified attribute in the HTML tag exists but is empty.
            If ``True``, returns the value specified in ``DEFAULT_EMPTY_FIELD_STRING``.
            Otherwise, returns an empty string.
        :param kwargs:
        """
        self.tag_types = tag_types
        self.tag_attrs = tag_attrs
        self.attr_to_extract = attr_to_extract
        self.fill_empty_field = fill_empty_field
        super().__init__(**kwargs)

    @supports_dynamic_parameters
    def run(self, website: Website, index: int = None) -> str:
        html_tag = website.find(self.tag_types, attrs=self.tag_attrs)

        try:
            content = sanitize_text(html_tag.attrs[self.attr_to_extract])
        except (AttributeError, KeyError):
            content = DEFAULT_EMPTY_FIELD_STRING

        # For cases where the attribute exists but is empty ("")
        if self.fill_empty_field:
            if content == "":
                content = DEFAULT_EMPTY_FIELD_STRING

        return content


class GeneralHttpHeaderFieldExtractor(BaseExtractor):
    def __init__(self, field_to_extract: str, fill_empty_field: bool = True, **kwargs):
        """General purpose extractor for extracting `HTTP header <https://developer.mozilla.org/en-US/docs/Web/HTTP/Headers>`__ fields."""
        self.field_to_extract = field_to_extract
        self.fill_empty_field = fill_empty_field
        super().__init__(**kwargs)

    @supports_dynamic_parameters
    def run(self, website: Website, index: int = None) -> str:
        headers = website.http_response.headers
        try:
            content = headers[self.field_to_extract]
        except KeyError:
            content = DEFAULT_EMPTY_FIELD_STRING

        if self.fill_empty_field:
            if content == "":
                content = DEFAULT_EMPTY_FIELD_STRING

        return content


class AccessTimeExtractor(BaseExtractor):
    def __init__(self, **kwargs):
        """Returns the current time as time of access. To be exact, the time of processing."""
        super().__init__(**kwargs)

    @supports_dynamic_parameters
    def run(self, website: Website, index: int = None) -> datetime:
        return datetime.now()


class CmsExtractor(BaseExtractor):
    def __init__(self, **kwargs):
        """Extract the Content Management System (CMS) used for building the website.

        Note: This method uses the HTML generator meta tag and some hard-coded search terms.
        Therefore, not all systems will be identified correctly."""
        super().__init__(**kwargs)

    @supports_dynamic_parameters
    def run(self, website: Website, index: int = None) -> str:
        cms_tag = website.find(_DEFAULT_CMS_TAG_TYPE, attrs=_DEFAULT_CMS_ATTRS, content=True)

        if cms_tag is not None:
            return cms_tag["content"]
        else:  # Detect some CM systems by keywords used in the HTML source code
            for cms, keywords in _DEFAULT_CMS_KEYWORDS.items():
                for word in keywords:
                    if word in website.html_text.lower():
                        return cms
            return DEFAULT_EMPTY_FIELD_STRING


class ContactNameExtractor(BaseExtractor):
    def __init__(self, tag_types: tuple = _DEFAULT_CONTACT_TAG_TYPES,
                 tag_attrs: dict = _DEFAULT_CONTACT_TAG_ATTRS,
                 separator: str = ";", **kwargs):
        """Find contact name(s) for a given website.

        :param tag_types: Specifies which kind of tags to look at (e. g., ``div`` or ``span``)
        :param tag_attrs: Provide additional attributes in a dictionary, e. g. ``{"class": "contact"}``.
        :param separator: When more than one contact is found, they are separated by the string given here.
        """
        self.tag_types = tag_types
        self.tag_attrs = tag_attrs
        self.separator = separator
        super().__init__(**kwargs)

    @supports_dynamic_parameters
    def run(self, website: Website, index: int = None) -> str:
        contact_tags = website.find_all(self.tag_types, attrs=self.tag_attrs)
        contacts = {sanitize_text(tag.text) for tag in contact_tags}

        if len(contacts) == 0:
            return DEFAULT_EMPTY_FIELD_STRING
        else:
            return self.separator.join(contacts)  # join list to return everything in one string


class CustomStringPutter(BaseExtractor):
    def __init__(self, string: Union[str, list], **kwargs):
        """Simply returns a given string or entry from a list of strings. Background: Sometimes, a column should be appended with a custom label for a given website (for example, an external ID).

        :param string: The string to be returned by the :meth:`~scrawler.data_extractors.CustomStringPutter.run` method.
            Can optionally pass a list here and use a different value for different URLs/domains that are scraped.
            In that case, remember to also pass ``use_index=True``.
        :raises IndexError: May raise an ``IndexError`` if a the parameter ``string`` is passed a list and ``use_index=True``.
            This may occur when you pass a list of custom strings shorter than the list of URLs crawled.
        """
        self.string = string

        super().__init__(**kwargs)

    @supports_dynamic_parameters
    def run(self, website: Website, index: int = None) -> str:
        return self.string


class DateExtractor(BaseExtractor):
    def __init__(self, tag_types: tuple = _DEFAULT_DATE_TAG_TYPES,
                 tag_attrs: dict = _DEFAULT_DATE_TAG_ATTRS,
                 return_year_month_day: bool = False, **kwargs):
        """
        Get dates by looking at passed tag. Can optionally parse dates to year, month and day.

        :param tag_types: Describes the tag types to find, e. g. ``meta``.
        :param tag_attrs: Specifies HTML attributes and their values in a key-value dict format.
            Example: ``{"name": "pubdate"}``.
        :param return_year_month_day: If True, returns date as 3 integers: year (``YYYY``), month (``MM``) and day (``dd``).
        """
        super().__init__(**kwargs)

        self.tag_types = tag_types
        self.tag_attrs = tag_attrs
        self.return_year_month_day = return_year_month_day
        self.n_return_values = 3 if self.return_year_month_day else 1

    @supports_dynamic_parameters
    def run(self, website: Website, index: int = None) -> Union[datetime, Tuple[int, int, int]]:
        date_tag = website.find(self.tag_types, attrs=self.tag_attrs, content=True)
        try:
            date_string = date_tag.attrs["content"]
            parsed_date = dateutil.parser.parse(date_string)  # returns a datetime object
            year, month, day = parsed_date.year, parsed_date.month, parsed_date.day
        except (AttributeError, ValueError, OverflowError):  # if pubdate_tag is None or date string can't be parsed
            parsed_date = DEFAULT_EMPTY_FIELD_STRING
            year, month, day = DEFAULT_EMPTY_FIELD_STRING, DEFAULT_EMPTY_FIELD_STRING, DEFAULT_EMPTY_FIELD_STRING

        if self.return_year_month_day:
            return year, month, day
        else:
            return parsed_date


class DescriptionExtractor(BaseExtractor):
    def __init__(self, **kwargs):
        """Get website description (the one shown in search engine results) using two common description fields."""
        super().__init__(**kwargs)

    @supports_dynamic_parameters
    def run(self, website: Website, index: int = None) -> str:
        standard_desc_tag = website.find(_DEFAULT_DESCRIPTION_TAG_TYPE, attrs=_DESCRIPTION_TAG_ATTRS_1, content=True)

        if standard_desc_tag is not None:
            description = standard_desc_tag.attrs["content"]

        if (standard_desc_tag is None) or (description == ""):
            other_desc_tag = website.find(_DEFAULT_DESCRIPTION_TAG_TYPE, attrs=_DESCRIPTION_TAG_ATTRS_2, content=True)
            if other_desc_tag is not None:
                description = other_desc_tag.attrs["content"]
            else:
                description = DEFAULT_EMPTY_FIELD_STRING

        return sanitize_text(description)


class DirectoryDepthExtractor(BaseExtractor):
    def __init__(self, **kwargs):
        """Returns the directory level that a given document is in.

        For example, ``https://www.sub.example.com/dir1/dir2/file.html`` returns 3."""
        super().__init__(**kwargs)

    @supports_dynamic_parameters
    def run(self, website: Website, index: int = None) -> int:
        return get_directory_depth(website.url)


class ExpiryDateExtractor(GeneralHttpHeaderFieldExtractor, DateExtractor, BaseExtractor):
    def __init__(self, return_year_month_day: bool = False, **kwargs):
        """Get website ``expiry`` date from HTTP header or HTML Meta tag."""
        GeneralHttpHeaderFieldExtractor.__init__(self, field_to_extract="Expires", **kwargs)
        DateExtractor.__init__(self, tag_types=("meta"), tag_attrs={"name": ["expires", "Expires", "EXPIRES"]},
                               return_year_month_day=return_year_month_day)

    @supports_dynamic_parameters
    def run(self, website: Website, index: int = None) -> Union[datetime, Tuple[int, int, int]]:
        header_date_string = GeneralHttpHeaderFieldExtractor.run(self, website, index)
        try:
            result = dateutil.parser.parse(header_date_string)
            if self.return_year_month_day:
                result = result.year, result.month, result.day
        except (ValueError, OverflowError):  # if date string can't be parsed
            result = DateExtractor.run(self, website, index)    # DateExtractor already respects return_year_month_day

        return result


class HtmlTextExtractor(BaseExtractor):
    def __init__(self, **kwargs):
        """Get plain HTML text of website."""
        super().__init__(**kwargs)

    @supports_dynamic_parameters
    def run(self, website: Website, index: int = None) -> int:
        return website.html_text


class HttpStatusCodeExtractor(BaseExtractor):
    def __init__(self, **kwargs):
        """Get status code of HTTP request."""
        super().__init__(**kwargs)

    @supports_dynamic_parameters
    def run(self, website: Website, index: int = None) -> int:
        try:
            return website.http_response.status
        except AttributeError:  # when website is fetch using fetch(), the response object is requests.Response
            return website.http_response.status_code


class KeywordsExtractor(GeneralHtmlTagExtractor, BaseExtractor):
    def __init__(self, **kwargs):
        """Get keywords from HTML keyword meta tag (if present)."""
        super().__init__(tag_types=_DEFAULT_KEYWORDS_TAG_TYPE, tag_attrs=_DEFAULT_KEYWORDS_TAG_ATTRS,
                         attr_to_extract="content", **kwargs)

    @supports_dynamic_parameters
    def run(self, website: Website, index: int = None) -> str:
        return super().run(website, index)


class LanguageExtractor(GeneralHtmlTagExtractor, BaseExtractor):
    def __init__(self, **kwargs):
        """Get language of a given website from its HTML tag ``lang`` attribute."""
        super().__init__(tag_types="html", tag_attrs={}, attr_to_extract="lang", **kwargs)

    @supports_dynamic_parameters
    def run(self, website: Website, index: int = None) -> str:
        return super().run(website, index).lower()


class LastModifiedDateExtractor(GeneralHttpHeaderFieldExtractor, DateExtractor, BaseExtractor):
    def __init__(self, return_year_month_day: bool = False, **kwargs):
        """Get website ``last-modified`` date from HTTP header or HTML Meta tag."""
        GeneralHttpHeaderFieldExtractor.__init__(self, field_to_extract="Last-Modified", **kwargs)
        DateExtractor.__init__(self, tag_types=("meta"), tag_attrs={"http-equiv": "last-modified"},
                               return_year_month_day=return_year_month_day)

    @supports_dynamic_parameters
    def run(self, website: Website, index: int = None) -> Union[datetime, Tuple[int, int, int]]:
        header_date_string = GeneralHttpHeaderFieldExtractor.run(self, website, index)
        try:
            result = dateutil.parser.parse(header_date_string)
            if self.return_year_month_day:
                result = result.year, result.month, result.day
        except (ValueError, OverflowError):  # if date string can't be parsed
            result = DateExtractor.run(self, website, index)    # DateExtractor already respects return_year_month_day

        return result


class LinkExtractor(BaseExtractor):
    def __init__(self, **kwargs):
        """Find all links from a website (without duplicates)."""
        super().__init__(**kwargs)

    @supports_dynamic_parameters
    def run(self, website: Website, index: int = None) -> set:
        link_tags = website.find_all("a", href=True)  # find all link tags <a> that have the attribute href
        links = {tag["href"].strip() for tag in link_tags}  # get the URL (hyper-reference, href)

        return links


class ServerProductExtractor(GeneralHttpHeaderFieldExtractor, BaseExtractor):
    def __init__(self, **kwargs):
        """Get website ``Server`` info from HTTP header."""
        super().__init__(field_to_extract="Server", **kwargs)

    @supports_dynamic_parameters
    def run(self, website: Website, index: int = None) -> str:
        return super().run(website, index)


class StepsFromStartPageExtractor(BaseExtractor):
    def __init__(self, **kwargs):
        """Returns the number of links that have to be followed from the start page to arrive at this website."""
        super().__init__(**kwargs)

    @supports_dynamic_parameters
    def run(self, website: Website, index: int = None) -> int:
        return website.steps_from_start_page


class MobileOptimizedExtractor(BaseExtractor):
    def __init__(self, **kwargs):
        """Checks whether website is optimized for mobile usage by looking up HTML ``viewport`` meta tag."""
        super().__init__(**kwargs)

    @supports_dynamic_parameters
    def run(self, website: Website, index: int = None) -> int:
        viewport_tag = website.find(_DEFAULT_IS_MOBILE_OPTIMIZED_TAG_TYPE, attrs=_DEFAULT_IS_MOBILE_OPTIMIZED_TAG_ATTRS,
                                    content=True)

        return 0 if (viewport_tag is None) else 1


class TermOccurrenceExtractor(BaseExtractor):
    def __init__(self, terms: Union[List[str], str], ignore_case: bool = False, **kwargs):
        """Checks if the given terms occur in the website's HTML text.
        Returns 0 if no term occurs in the soup's text, 1 if at least one occurs.

        :param terms: term or list of terms to search for.
        :param ignore_case: Whether to respect the text's casing (upper-/lowercase).
        """

        self.terms = [terms] if type(terms) is str else terms
        self.ignore_case = ignore_case

        super().__init__(**kwargs)

    @supports_dynamic_parameters
    def run(self, website: Website, index: int = None) -> int:
        text = website.html_text

        if self.ignore_case:
            text = text.lower()

        for term in self.terms:
            if term in text:
                return 1

        return 0


class TermOccurrenceCountExtractor(BaseExtractor):
    def __init__(self, terms: Union[List[str], str], ignore_case: bool = False, **kwargs):
        """Count the number of times the given terms occur in the website's HTML text.

        :param terms: term or list of terms to search for.
        :param ignore_case: Whether to respect the text's casing (upper-/lowercase).
        :returns: Total sum of all occurrences.
        """

        self.terms = [terms] if type(terms) is str else terms
        self.ignore_case = ignore_case

        super().__init__(**kwargs)

    @supports_dynamic_parameters
    def run(self, website: Website, index: int = None) -> int:
        text = website.html_text

        if self.ignore_case:
            text = text.lower()

        return sum([text.count(term) for term in self.terms])


class TitleExtractor(BaseExtractor):
    def __init__(self, **kwargs):
        """Get title of a website (the same that is shown in a browser in the tabs tray)."""
        super().__init__(**kwargs)

    @supports_dynamic_parameters
    def run(self, website: Website, index: int = None) -> str:
        try:
            return sanitize_text(website.title.string)
        except AttributeError:
            return DEFAULT_EMPTY_FIELD_STRING


class UrlExtractor(BaseExtractor):
    def __init__(self, **kwargs):
        """Returns the website's URL."""
        super().__init__(**kwargs)

    @supports_dynamic_parameters
    def run(self, website: Website, index: int = None) -> str:
        return website.url


class UrlBranchNameExtractor(BaseExtractor):
    def __init__(self, branch_name_position: int = 1, **kwargs):
        """Extract sub-domain names from URLs like ``subdomain.example.com``, which often refer to an entity's sub-branches.

        :param branch_name_position: Where in the URL to look for the name. If ``0``, the domain will be used.
            Otherwise, indexes into all available sub-domains:
            ``1`` would retrieve the first sub-domain *from the right*, ``2`` the second, and so on.
        """
        self.branch_name_position = branch_name_position
        super().__init__(**kwargs)

    @supports_dynamic_parameters
    def run(self, website: Website, index: int = None) -> str:
        if self.branch_name_position == 0:
            branch_name = website.parsed_url.domain
        else:
            try:
                branch_name = website.parsed_url.subdomain.split(".")[-self.branch_name_position]
            except IndexError:
                branch_name = DEFAULT_EMPTY_FIELD_STRING

        return branch_name


class UrlCategoryExtractor(BaseExtractor):
    def __init__(self, category_position: int = 2, **kwargs):
        """
        Try to identify the category of a given URL as the directory specified by :attr:`category_position`.

        :param category_position: Specify at which position in the path the category can be found.
        """
        self.category_position = category_position
        super().__init__(**kwargs)

    @supports_dynamic_parameters
    def run(self, website: Website, index: int = None) -> str:
        try:
            return website.parsed_url.path.split("/")[self.category_position].split(".")[0]
        except (AttributeError, IndexError):
            return DEFAULT_EMPTY_FIELD_STRING


class WebsiteTextExtractor(BaseExtractor):
    def __init__(self, mode: str = "auto",
                 min_length: int = 30,
                 tag_types: tuple = _DEFAULT_TEXT_TAG_TYPES,
                 tag_attrs: dict = _DEFAULT_TEXT_TAG_ATTRS,
                 allowed_string_types: List[NavigableString] = _DEFAULT_TEXT_ALLOWED_STRING_TYPES,
                 separator: str = "[SEP]", **kwargs):
        """Get readable website text, excluding ``<script>``, ``<style>``, ``<template>`` and other non-readable text.
        Several modes are available to make sure to only capture relevant text.

        :param mode: Default mode is ``auto``, which uses the ``readability`` algorithm to only extract a website's article text.
            If ``all_strings``, all readable website text (excluding script, style and other tags as well as HTML comments) will be retrieved.
            See also the `BeautifulSoup documentation <https://www.crummy.com/software/BeautifulSoup/bs4/doc/#get-text>`__ for the ``get_text()`` method.
            If ``by_length``, the :attr:`min_length` parameter will be used to determine the minimum length of HTML strings to be included in the text.
            If ``search_in_tags``, the tags dictionary will be used to identify the tags that include text.
        :param min_length: If using mode ``by_length``, this is the minimum length of a string to be considered.
            Shorter strings will be discarded.
        :param tag_types: Describes the tag types to find, e. g. ``div``.
        :param tag_attrs: Specifies HTML attributes and their values in a key-value dict format.
            Example: ``{"class": ["content", "main-content"]}``.

        :param allowed_string_types: List of types that are considered to be readable. This makes sure that scripts and similar types are excluded.
            Note that the types passed here have to inherit from :class:`bs4.NavigableString`.
        :param separator: String to be used as separator when concatenating all found strings.
        """
        self.mode = mode

        self.min_length = min_length
        self.tag_types = tag_types
        self.tag_attrs = tag_attrs

        self.allowed_string_types = allowed_string_types
        self.separator = separator

        super().__init__(**kwargs)

    @supports_dynamic_parameters
    def run(self, website: Website, index: int = None) -> str:
        def get_txt(obj: Union[Website, BeautifulSoup, Tag]) -> str:
            return BeautifulSoup.get_text(obj, separator=self.separator, strip=True, types=self.allowed_string_types)

        if self.mode == "auto":
            try:
                text = readability.Document(website.html_text).summary(html_partial=True)
            except Exception:
                text = DEFAULT_EMPTY_FIELD_STRING
        elif self.mode == "all_strings":
            text = get_txt(website)
        elif self.mode == "by_length":
            strings = website._all_strings(strip=True, types=self.allowed_string_types)
            strings = filter(lambda s: len(s) >= self.min_length, strings)
            text = self.separator.join(strings)
        elif self.mode == "search_in_tags":
            content_tags = website.find_all(self.tag_types, attrs=self.tag_attrs)

            if len(content_tags) == 0:  # None found
                text = DEFAULT_EMPTY_FIELD_STRING
            elif len(content_tags) == 1:
                text = get_txt(content_tags[0])
            else:
                texts = [get_txt(tag) for tag in content_tags]
                text = max(texts, key=len)  # choose tag with most text in it
        else:
            raise ValueError(f'Incorrect text search mode specified: "{self.mode}"')

        return sanitize_text(text)
