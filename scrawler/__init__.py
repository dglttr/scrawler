import logging

from scrawler.crawling import Crawler
from scrawler.scraping import Scraper
from scrawler.website import Website

__all__ = ["Crawler", "Scraper", "Website"]

logging.getLogger('readability').setLevel(logging.CRITICAL)     # to avoid a lot of noise in the output
