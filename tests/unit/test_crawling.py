import os
import sys
import unittest
from unittest.mock import MagicMock, patch
from dataclasses import asdict

# Get the absolute path to the back_end directory
back_end_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if back_end_path not in sys.path:
    sys.path.insert(0, back_end_path)

from crawling import perform_crawling
from generate_recent_news import GenerateRecentNews
from progress_sink import ProgressSink


class TestCrawling(unittest.TestCase):
    def test_perform_crawling_success(self):
        # Create test object
        recent_news = GenerateRecentNews(
            query="test query",
            query_meaning="test meaning",
            search_terms=["term1", "term2"],
            retrieved_urls=["https://www.bostonglobe.com/2025/04/02/nation/trump-tariffs-economy/", #Can be parsed using requests
                "https://www.fxstreet.com/analysis/quick-comments-on-the-markets-reaction-to-tariffs-202504031358", #Can be parsed using Crawlbase
                "https://seekingalpha.com/article/4772743-the-art-of-trump-trade-deal", #Cannot be parsed
                "https://www.reuters.com/markets/us/global-markets-view-usa-2025-04-03/"] #Cannot be parsed
        )
        sink = MagicMock(spec=ProgressSink)
        
        # Execute function
        result = perform_crawling(recent_news=recent_news, sink=sink)
        print(result.parsed_urls.keys())
        for url in result.parsed_urls:
            print(url, len(result.parsed_urls[url]))
        
        # Verify parsed_urls content
        self.assertIsInstance(result.parsed_urls, dict)
        self.assertGreaterEqual(len(result.parsed_urls), 2)
        
        # Check all URLs except the last two
        for url in recent_news.retrieved_urls[:-2]:
            self.assertIn(url, result.parsed_urls, f"URL {url} not found in the list of parsed URLs")
            self.assertIsInstance(result.parsed_urls[url], str, f"Content for {url} is not a string")
            self.assertGreaterEqual(len(result.parsed_urls[url]), 1000, 
                                  f"Content for {url} is too short: {len(result.parsed_urls[url])} chars")

    def test_perform_crawling_empty_urls(self):
        # Create test object with empty URLs
        recent_news = GenerateRecentNews(
            query="test query",
            query_meaning="test meaning",
            search_terms=["term1", "term2"],
            retrieved_urls=[]
        )
        sink = MagicMock(spec=ProgressSink)
        
        # Verify exception is raised
        with self.assertRaises(Exception) as context:
            perform_crawling(recent_news=recent_news, sink=sink)
        self.assertEqual(str(context.exception), "No URLs have been returned by the web search")


if __name__ == '__main__':
    unittest.main() 