"""Functions for web operations (e. g. working with URLs and retrieving data from websites)."""
from typing import Iterable, Union, Tuple, Callable
from urllib.parse import urljoin
from urllib.robotparser import RobotFileParser
import logging
import re

import requests
import tld
import tld.exceptions
import aiohttp

from scrawler.defaults import (DEFAULT_REQUEST_TIMEOUT, DEFAULT_REQUEST_TLS_VERIFICATION)


# CONSTANTS
DEFAULT_URL_SCHEMES = ("http:", "https:")
DEFAULT_TEXT_FILE_EXTENSIONS = ("html", "htm", "php", "cfm", "shtml", "xhtml", "asp", "aspx", "axd", "asx", "asmx", "ashx", "jsp")
DEFAULT_MEDIA_FILE_EXTENSIONS = ("pdf", "xml", "jpg", "jpeg", "png", "svg", "gif", "tiff", "tif", "ico", "mp4", "mp3",
                                 "zip", "exe", "avi", "css", "doc", "docx", "mid", "midi", "mpg", "mpeg", "mov", "qt",
                                 "ram", "rar", "txt", "wav", "7z", "tar.gz", "bin", "dmg", "iso", "csv", "dat", "db",
                                 "dbf", "log", "mdb", "sql")    # this list is not complete, but should cover the most frequent file extensions
DEFAULT_ALLOWED_HTTP_CONTENT_TYPE = "text/html"


async def async_get_html(url: str, session: aiohttp.ClientSession,
                         user_agent: str = None, verify: bool = DEFAULT_REQUEST_TLS_VERIFICATION,
                         max_content_length: int = -1, check_http_content_type: bool = True,
                         return_response_object: bool = False, raise_for_status: bool = False,
                         **kwargs) -> Union[str, Tuple[str, aiohttp.ClientResponse]]:
    """Collect HTML text of a given URL.

    :param url: URL to retrieve the HTML from.
    :param session: :class:`aiohttp:aiohttp.ClientSession` to be used for making the request asynchronously.
    :param user_agent: Allows to optionally specify a different user agent than the default Python user agent.
    :param verify: Whether to verify the server's TLS certificate. Useful if TLS connections fail, but should in general be ``True`` to avoid man-in-the-middle attacks.
    :param max_content_length: Check the HTTP header for the attribute ``content-length``. If it is bigger than this specified parameter, a ValueError is raised. Set to ``-1`` when not needed.
    :param check_http_content_type: Whether to check the HTTP header field ``content-type``. If it does not include ``text``, a ValueError is raised.
    :param return_response_object: If True, also returns the ClientResponse object from the GET request.
    :param raise_for_status: If True, raise an HTTPError if the HTTP request returned an unsuccessful status code.
    :param kwargs: Will be passed on to :meth:`aiohttp:aiohttp.ClientSession.get`.
    :return: HTML text from the given URL. Optionally also returns the HTTP response object.
    :raises aiohttp.ClientError, aiohttp.HTTPError, ValueError:
        Errors derived from :class:`aiohttp:aiohttp.ClientError` include ``InvalidURL``, ``ClientConnectionError`` and ``ClientResponseError``.
        May optionally raise ``aiohttp.HTTPError`` (if ``raise_for_status`` is ``True``)
        or ValueError (if ``check_http_content_type`` or ``max_content_length`` are ``True``).
    """
    headers = None if (user_agent is None) else {"user_agent": user_agent}

    async with session.get(url, verify_ssl=verify, headers=headers, raise_for_status=raise_for_status, **kwargs) as response:
        # Check if a different content type is declared in the HTTP header, e.g. 'application/pdf'
        if check_http_content_type:
            if "content-type" in response.headers:
                content_type = response.headers["content-type"]
                if not (DEFAULT_ALLOWED_HTTP_CONTENT_TYPE in content_type):
                    raise ValueError(f"Content type is not text: {content_type}")

        # Check if the content_length declared in the HTTP header exceeds the maximum specified in the method.
        if max_content_length >= 0:
            if "content-length" in response.headers:
                content_length = int(response.headers["content-length"])
                if content_length > max_content_length:
                    raise ValueError(f"Content length larger than specified length: Specified: {max_content_length}\tFound: {content_length}")

        text = await response.text()

    if return_response_object:
        return text, response
    else:
        return text


def extract_same_host_pattern(base_url: str) -> str:
    """Looks at the passed base/start URL to determine which mode for :func:`is_same_host` is appropriate.
        First looks at whether the given URL contains a non-empty path. If one is found, the number of directories ``X`` is counted and ``directoryX`` is returned.
        Otherwise, check whether the URL contains subdomains. If found, the number of subdomains ``X`` is counted and ``subdomainX`` is returned.
        If neither exist, returns ``fld``.

        .. seealso:: :func:`is_same_host`
    """
    u = ParsedUrl(base_url)

    path_cleaned = u.path
    path_cleaned = path_cleaned[1:] if path_cleaned[:1] == "/" else path_cleaned   # remove leading '/' TODO in the future replace with `removeprefix()` (>= Python 3.9)
    path_cleaned = path_cleaned[:-1] if path_cleaned[-1:] == "/" else path_cleaned   # remove trailing '/' TODO in the future replace with `removesuffix()` (>= Python 3.9)
    path_cleaned = path_cleaned if not ("." in path_cleaned) else "/".join(path_cleaned.split("/")[:-1])    # if URL points to a file, use the directory of the file

    subdomain_cleaned = u.subdomain.replace("www1.", "").replace("www.", "").replace("www1", "").replace("www", "")  # first replace www with dot, then without
    if path_cleaned != "":  # check for subdirectories
        subdirectory_depth = len(path_cleaned.split("/"))
        return f"directory{subdirectory_depth}"
    elif subdomain_cleaned != "":   # check for subdomains
        no_subdomains = len(subdomain_cleaned.split("."))
        return f"subdomain{no_subdomains}"
    else:   # if nothing else matches, use full domain
        return "fld"


def filter_urls(urls: Iterable,
                filter_non_standard_schemes: bool,
                filter_media_files: bool,
                blocklist: Iterable,
                filter_foreign_urls: Union[str, callable],
                base_url: str = None,
                return_discarded: bool = False,
                **kwargs) -> Union[set, Tuple[set, set]]:
    """Filter a list of URLs along some given attributes.

    :param urls: List of URLs to filter.
    :param filter_non_standard_schemes: If ``True``, makes sure that the URLs start with ``http:`` or ``https:``.
    :param filter_media_files: If ``True``, discards URLs having media file extensions like ``.pdf`` or ``.jpeg``. For details, see :func:`is_media_file`.
    :param blocklist: Specify a list of words or parts that if they appear in a URL, the URL will be discarded (e. g. 'git.', datasets.').
    :param filter_foreign_urls: Specify how to detect foreign URLs.
        Can either be a string that is passed to :func:`is_same_host()`, or a custom ``Callable`` that has to include two arguments, ``url1`` and ``url2``.
        For details on possible strings see :func:`is_same_host()` (note that the ``base_url`` parameter has to be passed for this to work).
        If you pass your own comparison function here, it has to include two parameters, ``url1`` and ``url2``.
        The first URL is the one to be checked, and the second is the reference (the crawling start URL). This function
        should return ``True`` for URLs that belong to the same host, and ``False`` for foreign URLs.
    :param base_url: Used in conjunction with the ``filter_foreign_urls`` parameter to detect foreign URLs.
    :param return_discarded: If ``True``, also returns to discarded URLs.
    :return: ``Set`` containing URLs that were not filtered. Optionally also returns discarded URLs.

    .. seealso::
       .. autosummary::
          :nosignatures:

          is_media_file
          is_same_host
    """
    filtered, discarded = set(), set()
    for url in urls:
        if filter_non_standard_schemes and not url.startswith(DEFAULT_URL_SCHEMES):
            discarded.add(url)
            continue
        if filter_media_files and is_media_file(url):
            discarded.add(url)
            continue
        if any([el in url for el in blocklist]):
            discarded.add(url)
            continue
        if base_url is not None:
            if isinstance(filter_foreign_urls, Callable):
                same_host = filter_foreign_urls(url, base_url)
            else:
                same_host = is_same_host(url, base_url, mode=filter_foreign_urls)

            if not same_host:
                discarded.add(url)
                continue
        filtered.add(url)

    if return_discarded:
        return filtered, discarded
    else:
        return filtered


def fix_relative_urls(urls: Iterable, base_url: str) -> set:
    """Make relative URLs absolute by joining them with the base URL that they were found on."""
    fixed = set()
    for url in urls:
        try:
            fixed.add(urljoin(base=base_url, url=url))
        except ValueError:  # catch invalid URLs
            continue
    return fixed


def get_html(url: str, timeout: int = DEFAULT_REQUEST_TIMEOUT, user_agent: str = None,
             verify: bool = DEFAULT_REQUEST_TLS_VERIFICATION, stream: str = True,
             max_content_length: int = -1, check_http_content_type: bool = True,
             return_response_object: bool = False, raise_for_status: bool = False) -> Union[Tuple[str, requests.Response], str]:
    """Collect HTML text of a given URL.

    :param url: URL to retrieve the HTML from.
    :param timeout: If the server does not answer for the number of seconds specified here, a :class:`Timeout` exception is raised.
    :param user_agent: Allows to optionally specify a different user agent than the default Python user agent.
    :param verify: Whether to verify the server's TLS certificate. Useful if TLS connections fail, but should in general be ``True`` to avoid man-in-the-middle attacks.
    :param stream: If ``True``, only the header of the response is retrieved. This allows for HTTP content type checking before actually retrieving the content. For details see the `Requests documentation <https://2.python-requests.org/en/master/user/advanced/#id9>`__.
    :param max_content_length: Check the HTTP header for the attribute ``content-length``. If it is bigger than this specified parameter, a ``ValueError`` is raised. Set to ``-1`` when not needed.
    :param check_http_content_type: Check the HTTP header for the attribute ``content-type``. If it does not include 'text', a ``ValueError`` is raised.
    :param return_response_object: If ``True``, also returns the ``Response`` object from the GET request.
    :param raise_for_status: If ``True``, raise an ``HTTPError`` if the HTTP request returned an unsuccessful status code.
    :return: HTML text from the given URL.
    :raises ConnectionError, Timeout, other RequestExceptions, HTTPError, ValueError: Raises some errors from the
        requests library when retrieval errors occur. Optionally raises ``HTTPError`` (if ``raise_for_status`` is ``True``) and
        ``ValueError`` (if ``check_http_content_type`` or ``max_content_length`` are ``True``).
    """
    response = requests.get(url, timeout=timeout, stream=stream, verify=verify, headers={"user_agent": user_agent})

    if raise_for_status:
        response.raise_for_status()  # throw an exception if HTTP requests returned an unsuccessful status code

    # Check if a different content type is declared in the HTTP header, e.g. 'application/pdf'
    if check_http_content_type:
        try:
            content_type = response.headers["content-type"]
            if not (DEFAULT_ALLOWED_HTTP_CONTENT_TYPE in content_type):
                raise ValueError(f"Content type is not text: {content_type}")
        except KeyError:  # Don't do anything if the attribute is not specified in the header
            pass

    # Check if the content_length declared in the HTTP header exceeds the maximum specified in the method.
    if max_content_length >= 0:
        try:
            content_length = int(response.headers["content-length"])
            if content_length > max_content_length:
                raise ValueError(f"Content length larger than specified length: Specified: {max_content_length}\tFound: {content_length}")
        except KeyError:  # Don't do anything if the attribute is not specified in the header
            pass

    if return_response_object:
        return response.text, response
    else:
        return response.text


async def async_get_redirected_url(url: str, session: aiohttp.ClientSession, max_redirects_to_follow: int = 100,
                                   **kwargs) -> str:
    """Find final, redirected URL. Supports both HTTP redirects and HTML redirects. Also follows up on multiple redirects.

    :param url: Original URL.
    :param session: ``aiohttp.ClientSession`` to be used for making the request asynchronously.
    :param max_redirects_to_follow: Maximum number of redirects to follow to guard against infinite redirects. If limit is reached, ``None`` is returned.
    :param kwargs: Passed on to :func:`async_get_html`.
    :returns: URL after redirects. If URL is invalid or an error occurs, returns ``None``.
    """
    redirect_counter = 0

    try:
        html, response = await async_get_html(url, session=session, max_redirects=max_redirects_to_follow,
                                              return_response_object=True, **kwargs)

        # HTML redirect (see https://www.w3docs.com/snippets/html/how-to-redirect-a-web-page-in-html.html)
        if len(re.findall('<meta.*http-equiv.*refresh.*', html, flags=re.IGNORECASE)) != 0:
            redirect_tag = re.findall('<meta.*http-equiv.*refresh.*', html, flags=re.IGNORECASE)[0]     # extract HTML refresh meta tag
            final_url = re.split('.*url.*=', redirect_tag, flags=re.IGNORECASE)[1].split('"')[0]    # extract URL part
            final_url = urljoin(base=url, url=final_url)    # make sure relative URLs are fixed
        # Redirect in HTTP refresh header
        elif "Refresh" in response.headers:
            final_url = re.split('.*url.*=', response.headers["Refresh"], flags=re.IGNORECASE)[1].split('"')[0]
            final_url = urljoin(base=url, url=final_url)
        else:
            final_url = str(response.url)

        # Possibly (recursively) follow redirects and re-fetch
        if final_url != url:
            if redirect_counter <= max_redirects_to_follow:     # guard against infinite redirects
                redirect_counter += 1
                final_url = await async_get_redirected_url(final_url, session=session, max_redirects_to_follow=max_redirects_to_follow, **kwargs)
            else:
                raise ValueError(f"Too many redirects on URL {url}")
    except Exception as e:
        logging.error(f"Unable to retrieve redirected URL from {url}. Details: {e.__repr__()}")
        final_url = None

    logging.info(f"Original URL: {url}\tURL after redirects: {final_url}")
    return final_url


def get_redirected_url(url: str, max_redirects_to_follow: int = 100, **kwargs) -> str:
    """Find final, redirected URL. Supports both HTTP redirects and HTML redirects. Also follows up on multiple redirects.

    :param url: Original URL.
    :param max_redirects_to_follow: Maximum number of redirects to follow to guard against infinite redirects. If limit is reached, ``None`` is returned.
    :param kwargs: Passed on to :func:`get_html`.
    :returns: URL after redirects. If URL is invalid or an error occurs, returns ``None``.
    """
    redirect_counter = 0

    try:
        html, response = get_html(url, return_response_object=True, **kwargs)

        # HTML redirect (see https://www.w3docs.com/snippets/html/how-to-redirect-a-web-page-in-html.html)
        if len(re.findall('<meta.*http-equiv.*refresh.*', html, flags=re.IGNORECASE)) != 0:
            redirect_tag = re.findall('<meta.*http-equiv.*refresh.*', html, flags=re.IGNORECASE)[0]     # extract HTML refresh meta tag
            final_url = re.split('.*url.*=', redirect_tag, flags=re.IGNORECASE)[1].split('"')[0]    # extract URL part
            final_url = urljoin(base=url, url=final_url)    # make sure relative URLs are fixed
        # Redirect in HTTP refresh header
        elif "Refresh" in response.headers:
            final_url = re.split('.*url.*=', response.headers["Refresh"], flags=re.IGNORECASE)[1].split('"')[0]
            final_url = urljoin(base=url, url=final_url)
        else:
            final_url = str(response.url)

        # Possibly (recursively) follow redirects and re-fetch
        if final_url != url:
            if redirect_counter <= max_redirects_to_follow:     # guard against infinite redirects
                redirect_counter += 1
                final_url = get_redirected_url(final_url, max_redirects_to_follow=max_redirects_to_follow, **kwargs)
            else:
                raise ValueError(f"Too many redirects on URL {url}")
    except Exception as e:
        logging.error(f"Unable to retrieve redirected URL from {url}. Details: {e}")
        final_url = None

    logging.info(f"Original URL: {url}\tURL after redirects: {final_url}")
    return final_url


async def async_get_robot_file_parser(start_url: str, session: aiohttp.ClientSession, **kwargs) -> Union[RobotFileParser, None]:
    """Returns :class:`~python:urllib.robotparser.RobotFileParser` from given URL.
    If no ``robots.txt`` file is found or error occurs, returns ``None``.

    :param start_url: URL from which ``robots.txt`` will be collected.
    :param session: ``aiohttp.ClientSession`` to use for making the request.
    :param kwargs: Will be passed to :func:`get_html`.
    :returns:
    """
    try:
        parsed_url = ParsedUrl(start_url)

        robot_txt_url = f"{parsed_url.scheme}://{parsed_url.netloc}/robots.txt"
        rp = RobotFileParser(robot_txt_url)

        text = await async_get_html(robot_txt_url, session=session, check_http_content_type=False,
                                    return_response_object=False, raise_for_status=True, **kwargs)

        lines = [line.strip() for line in text.split("\n") if line != '']
        rp.parse(lines)

        return rp
    except Exception as e:  # Exceptions from URL parsing, HTML retrieval and robot file parsing
        logging.warning(f"Unable to retrieve robots.txt from {start_url}. Reason: {e.__repr__()}")
        return None


def get_robot_file_parser(start_url: str, **kwargs) -> Union[RobotFileParser, None]:
    """Returns :class:`~python:urllib.robotparser.RobotFileParser` object from given URL.
    If no ``robots.txt`` file is found or error occurs, returns ``None``.

    :param start_url: URL from which ``robots.txt`` will be collected.
    :param kwargs: Will be passed to :func:`get_html`.

    .. seealso:: :func:`async_get_robot_file_parser`
    """
    try:
        parsed_url = ParsedUrl(start_url)

        robot_txt_url = f"{parsed_url.scheme}://{parsed_url.netloc}/robots.txt"
        rp = RobotFileParser(robot_txt_url)

        text = get_html(robot_txt_url, check_http_content_type=False, return_response_object=False,
                        raise_for_status=True, **kwargs)

        lines = [line.strip() for line in text.split("\n") if line != '']
        rp.parse(lines)

        return rp
    except Exception as e:  # Exceptions from URL parsing, HTML retrieval and robot file parsing
        logging.warning(f"Unable to retrieve robots.txt from {start_url}. Reason: {e}")
        return None


# TODO rethink whether computation is correct
#  example 1 should return 2, example 2 might return 1
def get_directory_depth(url: str) -> Union[int, None]:
    """
    Returns the directory level that a given document is in.
    For example, ``https://example.com/en/directoryA/document.html`` returns 3,
    because the ``document.html`` is 3 directories deep into the website's structure.
    Further, ``https://example.com/en/`` returns 1 (the trailing ``/`` is ignored), and ``https://example.com`` returns 0.

    :param url: URL to be checked which subdirectory is used.
    :return: Subdirectory level as path depth. If the URL is invalid, returns ``None``.
    """
    if url.endswith("/"):   # to ensure that path does not end with '/', making the length bigger than it is
        url = url[:-1]

    try:
        path = ParsedUrl(url).path
    except (tld.exceptions.TldBadUrl, tld.exceptions.TldDomainNotFound):
        return None
    return len(path.split("/")) - 1


def is_media_file(url: str, disallow_approach: bool = False, check_http_header: bool = False) -> bool:
    """
    Checks whether the URL ends in a file extension on an allowlist, indicating it is not a media file.

    :param url: URL to be checked.
    :param disallow_approach: If ``True``, uses a blocklist-approach, where file extensions known to be media file extensions are blocked.
        Note that while the blocklist used covers the most frequent file extensions, it certainly is not complete.
        Using the default allowlist-approach will guarantee no URLs with any but a text file extension are processed.
    :param check_http_header: Look up the HTTP header attribute ``content-type`` and checks whether it contains ``text/html``.
        Note that enabling this would make the function execute much slower, because an HTTP request is made
        instead of just checking a string.
    :return: ``True``/``False``
    """
    if check_http_header:
        try:
            content_type = requests.head(url).headers["content-type"]
            if DEFAULT_ALLOWED_HTTP_CONTENT_TYPE in content_type:
                return False
            else:
                return True
        except (requests.exceptions.RequestException, AttributeError, KeyError):
            pass

    try:
        path = ParsedUrl(url).path    # this is useful to remove query parameters and fragments
    except (tld.exceptions.TldBadUrl, tld.exceptions.TldDomainNotFound):   # mal-formed URLs
        return False

    if not ("." in path):   # no dot found -> no file ending exists
        return False

    last_part_of_path = path.split("/")[-1]
    suffix = last_part_of_path.split(".")[-1].lower()
    if disallow_approach:
        if suffix in DEFAULT_MEDIA_FILE_EXTENSIONS:
            return True
        else:
            return False
    else:
        if suffix in ("/", "") or suffix in DEFAULT_TEXT_FILE_EXTENSIONS:
            return False

    return True


def is_same_host(url1: str, url2: str, mode: str = "hostname") -> bool:
    """
    Checks whether two URLs have the same host. A comparison mode can be defined which determines the parts of the URLs that are checked for equality.

    :param url1: First URL to compare.
    :param url2: Second URL to compare.
    :param mode: String describing which URL parts to check for equality.
        Can either be any one of the attributes of the ParsedUrl class (e.g. ``domain``, ``hostname``, ``fld``).
        Alternatively, can be set to ``subdomainX`` with ``X`` representing an integer number up to which subdomain the URLs should be compared. E.g., comparing ``http://www.sub.example.com`` and ``http://blog.sub.example.com``, ``sub`` is the first level, while the second levels are ``www`` and ``blog``, respectively.
        Or, can be set to ``directoryX`` with ``X`` representing an integer number up to which directory the URLs should be compared. E.g., for ``http://example.com/dir1/dir2/index.html``, ``directory2`` would include all files in ``dir2``.
    :return: ``True`` or ``False``. If exceptions occur, the method returns ``False``.
    :raises ValueError: If invalid mode is specified.
    """
    try:
        url1 = ParsedUrl(url1)
        url2 = ParsedUrl(url2)
    except (tld.exceptions.TldBadUrl, tld.exceptions.TldDomainNotFound):   # URL couldn't be parsed
        return False

    if re.match(r"subdomain\d", mode):  # equal up to a certain sub-domain specified by an int
        try:
            index = int(mode[-1])
            return ((url1.fld == url2.fld)
                    and (url1.subdomain.split(".")[-index:] == url2.subdomain.split(".")[-index:]))
        except IndexError:
            return False
        except ValueError:
            raise ValueError(f"Invalid comparison mode in is_same_host(): {mode}. When specifying to check the subdomains, you have to include the subdomain level up to which the comparison will be made. Example: 'subdomain1'.")
    elif re.match(r"directory\d", mode):  # equal up to a certain directory specified by an int
        try:
            index = int(mode[-1]) + 1   # +1 because path begins with '/' -> first element of split will be empty string ''
            return ((url1.hostname == url2.hostname)
                    and url1.path.split("/")[:index] == url2.path.split("/")[:index])
        except IndexError:
            return False
        except ValueError:
            raise ValueError(f"Invalid comparison mode in is_same_host(): {mode}. When specifying to check the directories, you have to include the directory level up to which the comparison will be made. Example: 'directory1'.")
    else:
        try:
            return url1.__getattribute__(mode) == url2.__getattribute__(mode)
        except AttributeError:
            raise ValueError(f"Invalid comparison mode in is_same_host(): {mode}. The comparison attribute you specified does not exist on ParsedUrl. Has to be one of the following: {ParsedUrl.__slots__}")


def strip_unnecessary_url_parts(urls: Iterable, parameters: bool = False, fragments: bool = True) -> set:
    """Strip unnecessary URL parts.

    :param urls: URLs to be stripped (can be any Iterable).
    :param parameters: If ``True``, strips URL query parameters (always start with a ``?``) from the URL.
    :param fragments: If ``True``, strips URL fragments (introduced with ``#``), except for relevant fragments using Google's hash bang syntax.
    :return: Iterable of URLs, optionally without (query) parameters.
    """
    stripped = set()
    for url in urls:
        if parameters:
            url = url.split("?")[0]
        if fragments:
            if not ("#!" in url):   # Check if Google hash bang syntax is used
                url = url.split("#")[0]
        stripped.add(url)

    return stripped


class ParsedUrl:
    __slots__ = ("url", "domain", "subdomain", "fld", "tld", "scheme",
                 "netloc", "hostname", "path", "query", "fragment")   # using __slots__ for performance purposes

    def __init__(self, url: str):
        """Parse a URL string into its various parts.
        Basically a wrapper around ``tld.Result`` to make accessing elements easier.

        :param url: URL string to parse.
        :param fail_silently: Returns ``None`` instead of raising an exception.
        :raises Exception: Exceptions from `TLD package <https://github.com/barseghyanartur/tld>`__ if the URL is invalid.
        """
        url_object = tld.get_tld(url, as_object=True)

        # example: 'http://username:password@some.subdomain.example.co.uk/path1/path2?param="abc"#xyz'
        self.url = url
        self.domain = url_object.domain                  # 'example'
        self.subdomain = url_object.subdomain            # 'some.subdomain'
        self.fld = url_object.fld                        # 'example.co.uk'
        self.tld = url_object.tld                        # 'co.uk'
        self.scheme = url_object.parsed_url.scheme       # 'http'
        self.netloc = url_object.parsed_url.netloc       # 'username:password@some.subdomain.example.co.uk'
        self.hostname = url_object.parsed_url.hostname   # 'some.subdomain.example.co.uk'
        self.path = url_object.parsed_url.path           # '/path1/path2'
        self.query = url_object.parsed_url.query         # 'param="abc"'
        self.fragment = url_object.parsed_url.fragment   # 'xyz'

    def __repr__(self):
        return f"ParsedUrl(url={self.url}, domain={self.domain}, subdomain={self.subdomain}, fld={self.fld}, tld={self.tld}, scheme={self.scheme}, netloc={self.netloc}, hostname={self.hostname}, path={self.path}, query={self.query}, fragment={self.fragment})"
