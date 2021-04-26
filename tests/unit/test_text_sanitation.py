import unittest

from scrawler.utils.general_utils import sanitize_text


class TestTextSanitation(unittest.TestCase):
    def setUp(self) -> None:
        self.SAMPLES = {
            "Hello, this is <!-- not --> a comment.": 'Hello, this is  a comment.',
            "   Test Newline \n\rTest Tab\t\t Test Padding     ": 'Test Newline   Test Tab   Test Padding'
        }

    def test_samples(self):
        for sample, truth in self.SAMPLES.items():
            self.assertEqual(sanitize_text(sample), truth)
