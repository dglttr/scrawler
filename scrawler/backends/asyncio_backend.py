from typing import Union, Iterable, Callable
import asyncio
import logging

import aiohttp

from scrawler.utils.web_utils import (get_directory_depth, async_get_redirected_url, async_get_robot_file_parser,
                                      strip_unnecessary_url_parts, fix_relative_urls, filter_urls,
                                      extract_same_host_pattern)
from scrawler.defaults import DEFAULT_PAUSE_TIME
from scrawler.utils.general_utils import ProgressBar
from scrawler.attributes import SearchAttributes, ExportAttributes
from scrawler.data_extractors import LinkExtractor
from scrawler.utils.file_io_utils import export_to_csv
from scrawler.website import Website


async def async_crawl_domain(start_url: str,
                             session: aiohttp.ClientSession,
                             search_attributes: SearchAttributes,
                             export_attrs: ExportAttributes = None,
                             user_agent: str = None,
                             pause_time: float = DEFAULT_PAUSE_TIME,
                             respect_robots_txt: bool = True,
                             max_no_urls: int = float("inf"),
                             max_distance_from_start_url: int = float("inf"),
                             max_subdirectory_depth: int = float("inf"),
                             filter_non_standard_schemes: bool = True,
                             filter_media_files: bool = True,
                             blocklist: Iterable = (),
                             filter_foreign_urls: Union[str, Callable] = "auto",
                             strip_url_parameters: bool = False,
                             strip_url_fragments: bool = True,
                             return_type: str = "data",
                             progress_bar: ProgressBar = None,
                             current_index: int = None,
                             semaphore: asyncio.Semaphore = None,
                             **kwargs):
    """
    Collect data from all sites of a given domain. The sites within the domain are found automatically be iteratively searching for all links inside all pages.

    :param start_url: The first URL to be accessed. From here, links will be extracted and iteratively processed to find all linked sites.
    :param search_attributes: Dictionary specifying what to search for and how to search it.
    :param export_attrs: Optional. If specified, the crawled data is exported from within the crawl() function.

    :param user_agent: Optionally specify a user agent for making the HTTP request.
    :param pause_time: Time to wait between the crawling of 2 URLs (in seconds). This pause is mostly to avoid being flagged as spammer by websites.
    :param respect_robots_txt: Whether to respect the specifications made in the website's robots.txt file.

    :param max_no_urls: Maximum number of URLs to be crawled (safety limit for very large crawls).
    :param max_distance_from_start_url: Maximum number of links that have to be followed to arrive at a certain URL from the start_url.
    :param max_subdirectory_depth: Maximum sub-level of the host up to which to crawl. E.g., consider this schema: hostname/sub-directory1/sub-siteA.
        If you would want to crawl all URLs of the same level as 'sub-directory1', specify 1.
        sub-siteA will then not be found, but a site hostname/sub-directory2 or hostname/sub-siteB will be.

    :param filter_non_standard_schemes: See utils.web_utils.filter_urls() for explanation.
    :param filter_media_files: See utils.web_utils.filter_urls() for explanation.
    :param blocklist: See utils.web_utils.filter_urls() for explanation.
    :param filter_foreign_urls: See utils.web_utils.filter_urls() for explanation.

    :param strip_url_parameters: See utils.web_utils.strip_unnecessary_url_parts() for explanation.
    :param strip_url_fragments: See utils.web_utils.strip_unnecessary_url_parts() for explanation.

    :param return_type: Specify which values to return ("all", "none", "data").
    :param progress_bar: If a ProgressBar object is passed, prints a progress bar on the command line.
    :param current_index: Internal index needed to allow dynamic parameters (parameters where a list of values has been
        passed and only the values relevant to the currently processed URL should be used; for example, export_attrs may
        contain a list of filenames, and only the relevant filename for the currently processed URL should be used).

    :param semaphore: asyncio.Semaphore used for controlling the number of concurrent processes run.
    :param session: aiohttp.ClientSession used to make requests in a concurrent manner.

    :return: List of the data collected from all URLs that where found using start_url as starting point.
    """
    async with semaphore:
        # Fetch and update start URL (solves redirects)
        start_url = await async_get_redirected_url(start_url, session=session, user_agent=user_agent)
        if start_url is None:
            return None

        # Optionally get foreign URL matching pattern
        filter_foreign_urls = extract_same_host_pattern(start_url) if (
                    filter_foreign_urls == "auto") else filter_foreign_urls

        # Robots.txt parsing
        if respect_robots_txt:
            robots_txt_parser = await async_get_robot_file_parser(start_url, session=session, user_agent=user_agent)

        # Initiate some objects
        to_crawl = {start_url}
        processed = set()
        discarded = set()
        data = []

        url_and_distance = {start_url: 0}  # for parameter max_url_depth

        # Start logging progress bar on console
        if progress_bar is not None:
            progress_bar.update(iterations=0, total_length_update=1)

        while (len(to_crawl) > 0) and (len(data) < max_no_urls):
            next_url = to_crawl.pop()

            # Check if URL access is disallowed by robots.txt
            if respect_robots_txt and (robots_txt_parser is not None):
                ua = "*" if (user_agent is None) else user_agent
                if not robots_txt_parser.can_fetch(ua, next_url):
                    logging.info(f"URL access disallowed for crawler by robots.txt: {next_url}")
                    discarded.add(next_url)
                    if progress_bar is not None:
                        progress_bar.update(iterations=1)
                    continue

            # Crawl only up to the subdirectory depth specified in the parameter
            current_directory_depth = get_directory_depth(next_url)
            if current_directory_depth > max_subdirectory_depth:
                logging.warning(f"Subdirectory depth too deep ({current_directory_depth}): {next_url}")
                discarded.add(next_url)
                if progress_bar is not None:
                    progress_bar.update(iterations=1)
                continue

            # Crawl only up to a certain distance (links that had to be followed) from the start_url
            current_steps_from_start_page = url_and_distance[next_url]
            if current_steps_from_start_page > max_distance_from_start_url:
                logging.warning(f"Too many steps from start page ({current_steps_from_start_page}): {next_url}")
                discarded.add(next_url)
                if progress_bar is not None:
                    progress_bar.update(iterations=1)
                continue

            # Get Website object for further processing
            try:
                website = await Website(next_url, steps_from_start_page=current_steps_from_start_page).fetch_async(
                    session=session, user_agent=user_agent, check_http_content_type=filter_media_files)
            except Exception as e:
                logging.error(
                    f"{e.__class__.__module__}.{e.__class__.__name__} while processing {next_url}. Details: {e}")
                discarded.add(next_url)
                if progress_bar is not None:
                    progress_bar.update(iterations=1)
                continue

            # Collect the data from the website
            url_data = search_attributes.extract_all_attrs_from_website(website, index=current_index)
            data.append(url_data)

            # Collect all available hyperlinks from the website and pre-process + filter them
            found_urls = LinkExtractor().run(website) if (
                        current_steps_from_start_page < max_distance_from_start_url) else []

            found_urls = strip_unnecessary_url_parts(found_urls, parameters=strip_url_parameters,
                                                     fragments=strip_url_fragments)
            found_urls = fix_relative_urls(urls=found_urls, base_url=start_url)
            found_urls, filtered = filter_urls(found_urls, base_url=start_url,
                                               filter_foreign_urls=filter_foreign_urls,
                                               filter_non_standard_schemes=filter_non_standard_schemes,
                                               filter_media_files=filter_media_files,
                                               blocklist=blocklist,
                                               return_discarded=True)
            discarded = discarded.union(filtered)

            # All newly found URLs to working list (to_crawl) except those processed or discarded already
            processed.add(next_url)
            urls_to_add = found_urls.difference(processed, discarded, to_crawl)
            to_crawl.update(urls_to_add)

            # Add URL depth (distance from start) to each newly found URL
            for url in found_urls:
                if url in url_and_distance:  # do not overwrite URL depths that are already included
                    continue
                else:
                    url_and_distance[url] = current_steps_from_start_page + 1

            logging.debug(f"Processed {next_url}")

            # Update progress bar
            if progress_bar is not None:
                progress_bar.update(iterations=1, total_length_update=len(urls_to_add))

            # pause to avoid being flagged as spammer
            await asyncio.sleep(pause_time)

        # Optionally export files immediately
        if (export_attrs is not None) and (len(data) > 0):
            export_to_csv(data, current_index=current_index, **export_attrs.__dict__)

        if return_type == "all":  # TODO better return type definition?
            return data, to_crawl, processed, discarded, url_and_distance
        elif return_type == "data":
            return data
        else:
            return None


async def async_scrape_site(url: str, session: aiohttp.ClientSession,
                            search_attrs: SearchAttributes, export_attrs: ExportAttributes = None,
                            user_agent: str = None, current_index: int = None,
                            progress_bar: ProgressBar = None) -> list:
    """Scrape the data specified in search_attrs from one website.

    :param url: URL to be scraped.
    :param session: aiohttp.ClientSession used to make requests in a concurrent manner.
    :param search_attrs: Specify which data to collect/search for in the website.
    :param export_attrs: Specify how and where to export the collected data (as CSV).
    :param user_agent: Optionally specify a user agent for making the HTTP request.
    :param current_index: Internal index needed to allow dynamic parameters (parameters where a list of values has been
        passed and only the values relevant to the currently processed URL should be used; for example, export_attrs may
        contain a list of filenames, and only the relevant filename for the currently processed URL should be used).
    :param progress_bar: If a ProgressBar object is passed, prints a progress bar on the command line.
    :return: List of data collected from the website.
    """
    if progress_bar is not None:
        progress_bar.update(iterations=0, total_length_update=1)

    try:
        website = await Website(url).fetch_async(session, user_agent=user_agent)
        website_data = search_attrs.extract_all_attrs_from_website(website, index=current_index)
    except Exception as e:
        logging.error(f"{e.__class__.__module__}.{e.__class__.__name__} while processing {url}. Details: {e}")
        website_data = []

    if progress_bar is not None:
        progress_bar.update(iterations=1)

    # Optionally export files immediately
    if (export_attrs is not None) and (len(website_data) > 0):
        export_to_csv(website_data, current_index=current_index, **export_attrs.__dict__)
    else:
        return website_data  # TODO useful return values
