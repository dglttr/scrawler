from typing import Union, List, Any
import asyncio
from multiprocessing.dummy import Pool as ThreadPool

import aiohttp

from scrawler.defaults import DEFAULT_REQUEST_TIMEOUT, DEFAULT_MAX_NO_PARALLEL_PROCESSES, DEFAULT_BACKEND
from scrawler.utils.general_utils import timing_decorator, ProgressBar
from scrawler.attributes import SearchAttributes, ExportAttributes, CrawlingAttributes
from scrawler.utils.file_io_utils import export_to_csv, multithreaded_csv_export
from scrawler.utils.validation_utils import validate_input_params
from scrawler import backends
from scrawler.backends import asyncio_backend, multithreading_backend


class Crawler:
    def __init__(self, urls: Union[str, List[str]],
                 search_attributes: SearchAttributes,
                 export_attributes: ExportAttributes = None,
                 crawling_attributes: CrawlingAttributes = CrawlingAttributes(),
                 user_agent: str = None,
                 timeout: Union[int, aiohttp.ClientTimeout] = None,
                 backend: str = DEFAULT_BACKEND,
                 parallel_processes: int = DEFAULT_MAX_NO_PARALLEL_PROCESSES,
                 validate_input_parameters: bool = True):
        """Crawl a domain or multiple domains in parallel.

        :param urls: Start URL of domain to crawl or list of all URLs to crawl.
        :param search_attributes: Specify which data to collect/search for in websites.
        :param export_attributes: Specify how and where to export the collected data (as CSV).
        :param crawling_attributes: Specify how to conduct the crawling, e. g. how to filter irrelevant URLs or limits on the number of URLs crawled.
        :param user_agent: Optionally specify a user agent for making the HTTP request.
        :param timeout: Timeout to be used when making HTTP requests. Note that the values specified here apply to each request individually, not to an entire session.
            When using the :mod:`.asyncio_backend`, you can pass an :class:`aiohttp:aiohttp.ClientTimeout` object where you can specify detailed timeout settings.
            Alternatively, you can pass an integer that will be interpreted as total timeout for one request in seconds.
            If nothing is passed, a default timeout will be used.
        :param backend: "asyncio" to use the :mod:`.asyncio_backend` (faster when crawling many domains at once, but more unstable and may get hung).
                        "multithreading" to use the :mod:`~scrawler.backends.multithreading_backend` (more stable, but most likely slower).
                        See also `Why are there two backends? <getting_started.html#why-are-there-two-backends>`__
        :param parallel_processes: Number of concurrent processes/threads to use.
            Can be very large when using the ``asyncio`` backend.
            When using ``multithreading``, should not exceed 2x the CPU count on the machine running the crawling.
        :param validate_input_parameters: Whether to validate input parameters.
            Note that this validates that all URLs work and that the various attributes work together.
            However, the attributes themselves are also validated independently.
            You will need to also pass ``validate=False`` to the attributes individually to completely disable input validation.
        """
        self.urls = [urls] if (type(urls) is str) else urls     # cast to list because validation expects list of urls
        
        if validate_input_parameters:
            validate_input_params(urls=self.urls, search_attrs=search_attributes, export_attrs=export_attributes,
                                  crawling_attrs=crawling_attributes)

        self.search_attrs = search_attributes
        self.export_attrs = export_attributes
        self.crawling_attrs = crawling_attributes

        self.backend = backend

        self.user_agent = user_agent

        # Timeout only works with asyncio backend
        if self.backend == backends.ASYNCIO:
            if isinstance(timeout, aiohttp.ClientTimeout):
                self.timeout = timeout
            elif type(timeout) is int:  # interpret as total timeout in seconds
                self.timeout = aiohttp.ClientTimeout(total=timeout)
            else:
                self.timeout = aiohttp.ClientTimeout(total=DEFAULT_REQUEST_TIMEOUT)

        self.parallel_processes = parallel_processes

        self._progress_bar = ProgressBar(custom_message="Sites scraped:")

        self.data = None

    @timing_decorator
    def run(self, export_immediately: bool = False) -> List[List[List[Any]]]:
        """Execute the crawling task and return the results.

        :param export_immediately: May be used when crawling many sites at once. In order to prevent a :class:`MemoryError`,
            data will be exported as soon as it is ready and then discarded to make room for the next domains.
        :return: The result is a list with three layers.
            The first layer has one entry per crawled domain (result = [domain1, domain2, ...]).
            The second layer (representing each crawled domain) is a list with one entry per processed URL (domain = [url1, url2, ...]).
            The third layer (representing each URL) is a list with one entry per extracted datapoint (url = [datapoint1, datapoint2, ...]).
        """
        if export_immediately:
            return_type = "none"
            export_attrs = self.export_attrs
        else:
            return_type = "data"
            export_attrs = None

        if self.backend == backends.MULTITHREADING:
            # Prepare argument list
            urls_and_index = list(enumerate(self.urls))  # all URLs with their respective index

            # Define function with constant parameters pre-filled
            def crawl_domain_prefilled_params(current_index: int, domain: str):
                return multithreading_backend.crawl_domain(start_url=domain, search_attributes=self.search_attrs,
                                                           export_attrs=export_attrs, user_agent=self.user_agent,
                                                           current_index=current_index, return_type=return_type,
                                                           progress_bar=self._progress_bar,
                                                           **self.crawling_attrs.__dict__)

            # Map crawl_domain() function over all domains to have it work in parallel
            pool = ThreadPool(processes=self.parallel_processes)
            self.data = pool.starmap(crawl_domain_prefilled_params, urls_and_index)
            pool.close()
            pool.join()
        elif self.backend == backends.ASYNCIO:
            async def crawl_all_urls(urls: Union[str, List[str]]):
                semaphore = asyncio.BoundedSemaphore(self.parallel_processes)
                async with aiohttp.ClientSession(timeout=self.timeout) as session:
                    tasks = [asyncio_backend.async_crawl_domain(start_url=url, session=session, search_attributes=self.search_attrs,
                                                                export_attrs=export_attrs, user_agent=self.user_agent,
                                                                return_type=return_type, progress_bar=self._progress_bar, current_index=i,
                                                                semaphore=semaphore,
                                                                **self.crawling_attrs.__dict__)
                             for i, url in enumerate(urls)]
                    return await asyncio.gather(*tasks)

            self.data = asyncio.get_event_loop().run_until_complete(crawl_all_urls(self.urls))  # instead of asyncio.run() which throws RuntimeErrors, see https://github.com/aio-libs/aiohttp/issues/4324#issuecomment-676675779
        else:
            raise ValueError(f'Backend "{self.backend}" not supported.')

        return self.data

    def run_and_export(self, export_attrs: ExportAttributes = None) -> None:
        """Shorthand for ``Crawler.run(export_immediately=True)``.

        :param export_attrs: :class:`.ExportAttributes` object specifying export parameters.
        """
        if export_attrs is not None:
            self.export_attrs = export_attrs

        if self.export_attrs is None:
            raise ValueError("No export attributes have been passed.")

        self.run(export_immediately=True)

    def export_data(self, export_attrs: ExportAttributes = None) -> None:
        """Export data previously collected from crawling task.

        :param export_attrs: :class:`.ExportAttributes` object specifying export parameters.
        """
        ea = export_attrs if (export_attrs is not None) else self.export_attrs

        if ea is None:
            raise ValueError("No export attributes have been passed.")

        if self.data is None:
            print("No data to be exported. Execute the run() method before exporting.")
            return

        if len(self.data) == 1:
            export_to_csv(self.data[0], **ea.__dict__)
        else:
            multithreaded_csv_export(self.data, **ea.__dict__)
