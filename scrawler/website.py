import aiohttp
from bs4 import BeautifulSoup

from scrawler.utils.web_utils import ParsedUrl, get_html, async_get_html
from scrawler.defaults import DEFAULT_HTML_PARSER


class Website(BeautifulSoup):
    def __init__(self, url: str, steps_from_start_page: int = None):
        """The Website object is a wrapper around a `BeautifulSoup <https://www.crummy.com/software/BeautifulSoup/bs4/doc/>`__ object from a website's HTML text,
        while adding additional information such as the URL and the HTTP response when fetching the website.

        :param url: Website URL.
        :param steps_from_start_page: Specifies number of steps from start URL to reach the given URL.
            Note that this is an optional parameter used in conjunction with the Crawler object.
        :raises: Exceptions raised during URL parsing.
        """
        self.url = url
        self.parsed_url = ParsedUrl(self.url)    # this will raise an error if the URL is invalid

        self.steps_from_start_page = steps_from_start_page

    def fetch(self, **kwargs):
        """Fetch website from given URL and construct ``BeautifulSoup`` from response data.

        :param kwargs: Are passed on to :func:`.get_html`.
        :raises: Exceptions from making the request (using :func:`requests:requests.get`) and HTML parsing.
        :return: Website object with ``BeautifulSoup`` properties.
        """
        self.html_text, self.http_response = get_html(self.url, return_response_object=True, **kwargs)

        if self.html_text is not None:
            super().__init__(self.html_text, DEFAULT_HTML_PARSER)

        return self

    async def fetch_async(self, session: aiohttp.ClientSession, **kwargs):
        """Asynchronously fetch website from given URL and construct BeautifulSoup from response data.

        :param session: :class:`aiohttp:aiohttp.ClientSession` to be used for making the request asynchronously.
        :param kwargs: Are passed on to :func:`.async_get_html`.
        :raises: Exceptions from making the request (using :meth:`aiohttp:aiohttp.ClientSession.get`) and HTML parsing.
        :return: Website object with ``BeautifulSoup`` properties.
        """
        self.html_text, self.http_response = await async_get_html(self.url, session=session,
                                                                  return_response_object=True, **kwargs)

        if self.html_text is not None:
            super().__init__(self.html_text, DEFAULT_HTML_PARSER)

        return self

    def _reconstruct_soup(self) -> None:
        """Reconstruct the underlying ``BeautifulSoup`` object from the fetched HTML text.
        May be useful when inplace changes to the object have been made and you want to recreate the object without having the fetch the HTML text again.
        Note that object construction comes with a performance penalty.
        """
        try:
            super().__init__(self.html_text, DEFAULT_HTML_PARSER)
        except (AttributeError, TypeError):
            print("Cannot reconstruct soup before HTML text has been fetched.")
