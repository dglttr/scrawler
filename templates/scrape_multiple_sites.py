# IMPORTS
# Do not make any changes here
####################################################################################################
from scrawler import Scraper
from scrawler.attributes import SearchAttributes, ExportAttributes
from scrawler.defaults import DEFAULT_CSV_SEPARATOR
from scrawler.data_extractors import *

# SETUP
# Please carefully review and adjust the settings below
####################################################################################################
URLS_TO_SCRAPE = ["https://www.example1.com", "https://www.example2.com", "https://www.example3.com"]

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
    fn=["scraped_data_e1", "scraped_data_e2", "scraped_data_e3"],
    header=["URL", "Title", "Description", "Keywords", "Contact", "Language", "Last modified",
            "Content Management System", "Copyright", "Text"],
    separator=DEFAULT_CSV_SEPARATOR
)


USER_AGENT = None   # If the server refuses the connection to the scraper, try setting a user agent here


# EXECUTION
# No changes necessary here
####################################################################################################
scraper = Scraper(URLS_TO_SCRAPE,
                  search_attributes=search_attrs,
                  export_attributes=export_attrs,
                  user_agent=USER_AGENT)
scraper.run()
scraper.export_data(export_as_one_file=True)
