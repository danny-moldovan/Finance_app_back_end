import os
import sys
import unittest
from multiprocessing import Queue
from unittest.mock import patch

# Get the absolute path to the back_end directory
back_end_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if back_end_path not in sys.path:
    sys.path.insert(0, back_end_path)

from websearch import perform_web_search
from progress_sink import ProgressSink
from generate_recent_news import GenerateRecentNews


class TestWebSearch(unittest.TestCase):
    def setUp(self):
        self.queue = Queue()
        self.sink = ProgressSink(self.queue)
        self.recent_news = GenerateRecentNews(
            query="test query",
            query_meaning="test meaning",
            search_terms=["term1", "term2"]
        )

    def test_perform_web_search_success(self):
        """Test successful execution of perform_web_search with normal search results."""
        mock_search_results = {
            "term1": ["url1", "url2"],
            "term2": ["url2", "url3"]
        }
        
        with patch('websearch.websearch_client.search_web', side_effect=lambda term: {'search_results': mock_search_results[term]}):
            result = perform_web_search(recent_news=self.recent_news, sink=self.sink)

            # Verify the result is a GenerateRecentNews object with correct attributes
            self.assertIsInstance(result, GenerateRecentNews)
            self.assertEqual(result.query, "test query")
            self.assertEqual(result.query_meaning, "test meaning")
            self.assertEqual(result.search_terms, ["term1", "term2"])
            self.assertEqual(result.retrieved_urls, ["url1", "url2", "url3"])

    def test_perform_web_search_empty_terms(self):
        """Test that perform_web_search raises an exception when search_terms is empty."""
        self.recent_news = GenerateRecentNews(
            query="test query",
            query_meaning="test meaning",
            search_terms=[]
        )
        
        with self.assertRaises(Exception) as context:
            perform_web_search(recent_news=self.recent_news, sink=self.sink)
        self.assertEqual(str(context.exception), "Search terms have not been generated")

    def test_perform_web_search_empty_results(self):
        """Test perform_web_search when search results are empty."""
        mock_search_results = {
            "term1": [],
            "term2": []
        }
        
        with patch('websearch.websearch_client.search_web', side_effect=lambda term: {'search_results': mock_search_results[term]}):
            result = perform_web_search(recent_news=self.recent_news, sink=self.sink)

            # Verify the result has empty retrieved_urls
            self.assertIsInstance(result, GenerateRecentNews)
            self.assertEqual(result.retrieved_urls, [])

    def test_perform_web_search_duplicate_results(self):
        """Test perform_web_search when there are duplicate URLs across different search terms."""
        mock_search_results = {
            "term1": ["url1", "url2", "url3"],
            "term2": ["url2", "url3", "url4"]
        }
        
        with patch('websearch.websearch_client.search_web', side_effect=lambda term: {'search_results': mock_search_results[term]}):
            result = perform_web_search(recent_news=self.recent_news, sink=self.sink)
            #print('Retrieved URLs: ', result.retrieved_urls)

            # Verify the result has deduplicated URLs
            self.assertIsInstance(result, GenerateRecentNews)
            expected_urls = ["url1", "url2", "url3", "url4"]
            self.assertEqual(len(result.retrieved_urls), len(expected_urls))
            for i in range(len(expected_urls)):
                self.assertEqual(result.retrieved_urls[i], expected_urls[i])
            # Verify that the URLs are sorted
            self.assertEqual(result.retrieved_urls, sorted(result.retrieved_urls))

    def test_perform_web_search_empty_term(self):
        """Test perform_web_search when one of the search terms returns no results."""
        mock_search_results = {
            "term1": ["url1", "url2"],
            "term2": []
        }
        
        with patch('websearch.websearch_client.search_web', side_effect=lambda term: {'search_results': mock_search_results[term]}):
            result = perform_web_search(recent_news=self.recent_news, sink=self.sink)

            # Verify the result only includes URLs from the successful search
            self.assertIsInstance(result, GenerateRecentNews)
            self.assertEqual(result.retrieved_urls, ["url1", "url2"])

if __name__ == '__main__':
    unittest.main() 