import unittest
import asyncio

import aiohttp

from scrawler.utils.web_utils import (async_get_redirected_url, async_get_robot_file_parser, get_directory_depth, is_media_file,
                                      is_same_host, strip_unnecessary_url_parts)


class TestGetRedirectedUrl(unittest.TestCase):
    def test_sample_redirects(self):
        # key=test URL, value=target as resolved by Firefox browser
        redirect_test_urls = {
            "https://crawler-test.com/redirects/redirect_1": "https://crawler-test.com/redirects/redirect_target",
            "https://crawler-test.com/redirects/redirect_2": "https://crawler-test.com/redirects/redirect_target",
            "https://crawler-test.com/redirects/redirect_3_302": "https://crawler-test.com/redirects/redirect_target",
            "https://crawler-test.com/redirects/redirect_4_307": "https://crawler-test.com/redirects/redirect_target",
            "https://crawler-test.com/redirects/disallowed_redirect": "https://crawler-test.com/redirects/redirect_target",
            "https://crawler-test.com/redirects/redirect_chain_allowed": "https://crawler-test.com/redirects/redirect_target",
            "https://crawler-test.com/redirects/disallowed_redirect_target_redirect": "https://crawler-test.com/redirects/disallowed_redirect_target",
            "https://crawler-test.com/redirects/infinite_redirect": None,
            "https://crawler-test.com/redirects/two_step_redirect_loop_1": None,
            "https://crawler-test.com/redirects/external_redirect": "https://www.deepcrawl.com/",
            "https://crawler-test.com/redirects/invalid_redirect": "https://crawler-test.com/images/foo.jpg",
            "https://crawler-test.com/redirects/meta_redirect_1": "https://crawler-test.com/redirects/redirect_target",
            "https://crawler-test.com/redirects/meta_redirect_2": "https://crawler-test.com/redirects/redirect_target",
            "https://crawler-test.com/redirects/meta_redirect_3": "https://crawler-test.com/redirects/redirect_target",
            "https://crawler-test.com/redirects/infinite_meta_redirect": "https://crawler-test.com/redirects/infinite_meta_redirect",
            "https://crawler-test.com/redirects/external_meta_redirect": "https://www.semetrical.com/",
            "https://crawler-test.com/redirects/invalid_meta_redirect": "https://crawler-test.com/images/foo.jpg",
            "https://crawler-test.com/redirects/header_refresh_redirect": "https://crawler-test.com/redirects/redirect_target",
            "https://crawler-test.com/redirects/redirect_to_404": "https://crawler-test.com/redirects/redirect_to_404_target",
            "https://crawler-test.com/redirects/reverse_redirect/14": "https://crawler-test.com/redirects/redirect_target",
            "https://crawler-test.com/redirects/redirect_content": "https://crawler-test.com/",
            "https://crawler-test.com/redirects/external_redirect_chain1": "https://www.deepcrawl.com",

            "https://crawler-test.com/redirects/redirect_303": "https://crawler-test.com/redirects/redirect_target",
            "https://crawler-test.com/redirects/redirect_304": "https://crawler-test.com/redirects/redirect_304",
            "https://crawler-test.com/redirects/redirect_305": "https://crawler-test.com/redirects/redirect_305",
            "https://crawler-test.com/redirects/redirect_306": "https://crawler-test.com/redirects/redirect_306",
            "https://crawler-test.com/redirects/redirect_308": "https://crawler-test.com/redirects/redirect_target",
        }   # exclude JavaScript redirects

        known_failures = {
            "https://crawler-test.com/redirects/redirect_300": "https://crawler-test.com/redirects/redirect_target"     # reason: multiple choices status code not supported by aiohttp
        }

        async def assert_redirect(test, target, session):
            detected_url = await async_get_redirected_url(test, session=session)
            self.assertEqual(detected_url, target, msg=f"Unsuccessful redirect detection. \n\tTest URL: {test}\nTarget: {target}\nDetected: {detected_url}")

        async def assert_all():
            async with aiohttp.ClientSession() as session:
                tasks = [assert_redirect(test, target, session=session)
                         for test, target in redirect_test_urls.items()]
                return await asyncio.gather(*tasks)

        asyncio.get_event_loop().run_until_complete(assert_all())


class TestGetRobotFileParser(unittest.TestCase):
    def setUp(self) -> None:
        self.URL = "https://crawler-test.com/"

        self.disallowed = [
            "https://crawler-test.com/robots_protocol/robots_excluded",
            "https://crawler-test.com/robots_protocol/robots_excluded_1/bar/baz",
            "https://crawler-test.com/robots_protocol/robots_excluded_2/foo",
            "https://crawler-test.com/robots_protocol/robots_excluded_3",
            "https://crawler-test.com/robots_protocol/robots_excluded_blank_line",
            "https://crawler-test.com/robots_protocol/robots_excluded_duplicate_description"
        ]

        self.allowed = [
            "https://crawler-test.com/robots_protocol/page_allowed_with_robots",
            "https://crawler-test.com/robots_protocol/allowed_longer"
        ]

        async def retrieve_async_parser():
            async with aiohttp.ClientSession() as session:
                return await async_get_robot_file_parser(self.URL, session=session)

        self.robot_file_parser = asyncio.run(retrieve_async_parser())

    def test_samples(self):
        for url in self.disallowed:
            self.assertFalse(self.robot_file_parser.can_fetch("*", url), msg=f"URL wrongly allowed for {url}")

        # Not parsed corectly by RobotFileParser, but function get_robot_file_parser() works
        # for url in self.allowed:
        #     self.assertTrue(self.robot_file_parser.can_fetch("*", url), msg=f"URL wrongly disallowed for {url}")


class TestGetDirectoryDepth(unittest.TestCase):
    def setUp(self) -> None:
        self.SAMPLES = {
            "https://example.com/en/directoryA/document.html": 3,
            "https://example.com/en/": 1,
            "https://example.com/en": 1,
            "https://example.com/en/directoryA/documents/": 3,
            "https://example.com/en/directoryA/documents/dirB/index.html": 5,
            "https://example.com/": 0,
            "https://example.com": 0
        }

    def test_samples(self):
        for url, depth_target in self.SAMPLES.items():
            self.assertEqual(get_directory_depth(url), depth_target)


class TestIsMediaFile(unittest.TestCase):
    def setUp(self) -> None:
        self.SAMPLES = {
            "https://example.com/en/directoryA/document.html": False,
            # TODO
        }

    def test_samples(self):
        for url, target in self.SAMPLES.items():
            self.assertEqual(is_media_file(url), target)


class TestIsSameHost(unittest.TestCase):
    def setUp(self) -> None:
        self.SAMPLES_SAME_HOST = [
            ["https://example.com/", "https://example.com", "domain"]
            # TODO modes = "domain", "fld", "hostname", "subdomainX", "directoryX"
        ]

        self.SAMPLES_DIFFERENT_HOST = [
            ["https://example.com/", "https://www.example.com", "hostname"]
            # TODO
        ]

    def test_samples(self):
        for url1, url2, mode in self.SAMPLES_SAME_HOST:
            self.assertTrue(is_same_host(url1, url2, mode=mode))

        for url1, url2, mode in self.SAMPLES_DIFFERENT_HOST:
            self.assertFalse(is_same_host(url1, url2, mode=mode))


class TestStripUnnecessaryUrlParts(unittest.TestCase):
    def setUp(self) -> None:
        self.SAMPLES_PARAMS = {
            "https://example.com?test": "https://example.com",
            "https://example.com/?test": "https://example.com/",
        }

        self.SAMPLES_FRAGMENTS = {
            "https://example.com#frag": "https://example.com",
            "https://example.com#!frag": "https://example.com#!frag",  # Google Hashbang syntax
        }

        self.SAMPLES_BOTH = {
            "https://example.com?id=1234#frag": "https://example.com"
        }

    def test_samples(self):
        for url, target in self.SAMPLES_PARAMS.items():
            self.assertEqual(strip_unnecessary_url_parts([url], parameters=True, fragments=False).pop(),
                             target)

        for url, target in self.SAMPLES_FRAGMENTS.items():
            self.assertEqual(strip_unnecessary_url_parts([url], parameters=False, fragments=True).pop(),
                             target)

        for url, target in self.SAMPLES_BOTH.items():
            self.assertEqual(strip_unnecessary_url_parts([url], parameters=True, fragments=True).pop(),
                             target)


if __name__ == "__main__":
    unittest.main()
