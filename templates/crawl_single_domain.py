# IMPORTS
# Do not make any changes here
####################################################################################################
from scrawler import Crawler
from scrawler.attributes import SearchAttributes, ExportAttributes, CrawlingAttributes
from scrawler.defaults import (DEFAULT_CSV_SEPARATOR, DEFAULT_PAUSE_TIME)
from scrawler.data_extractors import *

# SETUP
# Please carefully review and adjust the settings below
####################################################################################################
DOMAIN_TO_CRAWL = "https://www.example.com"

# Search attributes - Specify which data to collect/search for in the website
search_attrs = SearchAttributes(
    UrlExtractor(),
    TitleExtractor(),
    DescriptionExtractor(),
    KeywordsExtractor(),
    ContactNameExtractor(tag_types=("div", "span"), tag_attrs={"class": ["name", "employee_name"]}),
    LanguageExtractor(),
    DateExtractor(tag_types=("meta"), tag_attrs={"name": "pubdate"}),
    CmsExtractor(),
    GeneralHtmlTagExtractor(tag_types=("meta"), tag_attrs={"name": "copyright"}, attr_to_extract="content"),   # custom to extract the copyright notice
    WebsiteTextExtractor(mode="by_length", min_length=30)   # alternatively, the mode 'search_in_tags' can be chosen (see utils.data_extractors.WebsiteTextExtractor()) for more information)
)

# Export attributes - Specify how and where to export the collected data.
export_attrs = ExportAttributes(
    directory=r"C:\Users\USER\Documents",
    fn="crawled_data",
    header=["URL", "Title", "Description", "Keywords", "Contact", "Language", "Last modified",
            "Content Management System", "Copyright", "Text"],
    separator=DEFAULT_CSV_SEPARATOR
)

# Crawling attributes - Specify how to conduct the crawling, e. g. how to filter irrelevant URLs or limits on the number of URLs crawled.
crawling_attrs = CrawlingAttributes(
    filter_non_standard_schemes=True,
    filter_media_files=True,
    filter_foreign_urls="fld",
    blocklist=("git.", "datasets.", "nextcloud."),

    strip_url_parameters=False,
    strip_url_fragments=True,

    max_no_urls=None,
    max_subdirectory_depth=None,
    max_distance_from_start_url=None,

    pause_time=DEFAULT_PAUSE_TIME,
    respect_robots_txt=True
)

USER_AGENT = None   # If the server refuses the connection to the scraper, try setting a user agent here


# EXECUTION
# No changes necessary here
####################################################################################################
crawler = Crawler(DOMAIN_TO_CRAWL,
                  search_attributes=search_attrs,
                  crawling_attributes=crawling_attrs,
                  export_attributes=export_attrs,
                  user_agent=USER_AGENT)
crawler.run()
crawler.export_data()
