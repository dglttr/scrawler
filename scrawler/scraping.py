from typing import Union, List, Any
import asyncio
from multiprocessing.dummy import Pool as ThreadPool

import aiohttp

from scrawler.utils.general_utils import timing_decorator, ProgressBar
from scrawler.attributes import SearchAttributes, ExportAttributes
from scrawler.utils.file_io_utils import export_to_csv, multithreaded_csv_export
from scrawler.utils.validation_utils import validate_input_params
from scrawler.defaults import DEFAULT_REQUEST_TIMEOUT, DEFAULT_NO_CONCURRENT_REQUESTS_PER_HOST, DEFAULT_BACKEND
from scrawler import backends


class Scraper:
    def __init__(self, urls: Union[list, str],
                 search_attributes: SearchAttributes,
                 export_attributes: ExportAttributes = None,
                 user_agent: str = None,
                 timeout: Union[int, aiohttp.ClientTimeout] = None,
                 backend: str = DEFAULT_BACKEND,
                 validate_input_parameters: bool = True):
        """Scrape website or multiple websites in parallel.

        :param urls: Website URL or list of all URLs to scrape.
        :param search_attributes: Specify which data to collect/search for in websites.
        :param export_attributes: Specify how and where to export the collected data (as CSV).
        :param user_agent: Optionally specify a user agent for making the HTTP request.
        :param timeout: Timeout to be used when making HTTP requests. Note that the values specified here apply to each request individually, not to an entire session.
            You can pass an aiohttp.ClientTimeout object where you can specify detailed timeout settings. See the documentation at https://docs.aiohttp.org/en/stable/client_reference.html#aiohttp.ClientTimeout.
            Alternatively, you can pass an integer that will be interpreted as total timeout for one request in seconds.
            If nothing is passed, a default timeout will be used.
        :param backend: 'multithreading' (more stable, but most likely slower) or
                        'asyncio' (faster when crawling many domains at once, but more unstable and may get hung).
        :param validate_input_parameters: Whether to validate input parameters.
            Note that this validates that all URLs work and that the various attributes work together.
            However, the attributes themselves are also validated independently.
            You will need to also pass validate=False to the attributes to completely disable input validation.
        """
        self.urls = [urls] if (type(urls) is str) else urls     # cast to list because validation expects list of urls
        
        if validate_input_parameters:
            validate_input_params(urls=self.urls, search_attrs=search_attributes, export_attrs=export_attributes)

        self.search_attrs = search_attributes
        self.export_attrs = export_attributes

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

        self._progress_bar = ProgressBar(custom_message="Sites scraped:")

        self.data = None

    @timing_decorator
    def run(self, export_immediately: bool = False) -> List[List[Any]]:
        """Execute the scraping task and return the results.

        :param export_immediately: May be used when scraping many sites at once. In order to prevent a `MemoryError`,
            data will be exported as soon as it is ready and then discarded to make room for the next sites.
        :return: The result is a list  with one entry per processed URL (result = [url1, url2, ...]).
            Each URL entry is a list with one entry per extracted datapoint (url = [datapoint1, datapoint2, ...]).
        """
        export_attrs = self.export_attrs if export_immediately else None

        if self.backend == backends.MULTITHREADING:
            urls_and_index = list(enumerate(self.urls))

            # Define function with constant parameters pre-filled
            def scrape_site_params_prefilled(current_index: int, url: str):
                return backends.multithreading_backend.scrape_site(url, export_attrs=export_attrs, search_attrs=self.search_attrs,
                                                          current_index=current_index, user_agent=self.user_agent,
                                                          progress_bar=self._progress_bar)

            # Map to ThreadPool
            pool = ThreadPool()
            self.data = pool.starmap(scrape_site_params_prefilled, urls_and_index)
            pool.close()
            pool.join()
        elif self.backend == ASYNCIO:
            async def scrape_all_urls(urls):
                connector = aiohttp.TCPConnector(limit_per_host=DEFAULT_NO_CONCURRENT_REQUESTS_PER_HOST)
                async with aiohttp.ClientSession(timeout=self.timeout, connector=connector) as session:
                    tasks = [backends.asyncio_backend.async_scrape_site(url, session=session, search_attrs=self.search_attrs,
                                                               export_attrs=export_attrs, current_index=i,
                                                               user_agent=self.user_agent, progress_bar=self._progress_bar)
                             for i, url in enumerate(urls)]
                    return await asyncio.gather(*tasks)

            self.data = asyncio.get_event_loop().run_until_complete(scrape_all_urls(self.urls))  # instead of asyncio.run() which throws RuntimeErrors, see https://github.com/aio-libs/aiohttp/issues/4324#issuecomment-676675779
        else:
            raise ValueError(f'Backend "{self.backend}" not supported.')

        return self.data

    def run_and_export(self, export_attrs: ExportAttributes = None) -> None:
        """Shorthand for `Scraper.run(export_immediately=True)`.

        :param export_attrs: Object specifying export parameters.
        """
        if export_attrs is not None:
            self.export_attrs = export_attrs

        if self.export_attrs is None:
            raise ValueError("No export attributes have been passed.")

        self.run(export_immediately=True)

    def export_data(self, export_attrs: ExportAttributes = None, export_as_one_file: bool = True) -> None:
        """Export data previously collected from scraping task.

        :param export_attrs: Object specifying export parameters.
        :param export_as_one_file: If True, the data will be exported in one CSV file, each line representing one scraped URL.
        """
        ea = export_attrs if (export_attrs is not None) else self.export_attrs

        if ea is None:
            raise ValueError("No export attributes have been passed.")

        if self.data is None:
            print("No data to be exported. Execute the run() method before exporting.")
            return

        if export_as_one_file:
            export_to_csv(self.data, **ea.__dict__)
        else:
            if len(self.data) == 1:
                export_to_csv(self.data[0], **ea.__dict__)
            else:
                multithreaded_csv_export(self.data, **ea.__dict__)
