import unittest
from unittest.mock import patch, MagicMock
import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from identification_of_relevant_articles import identify_relevant_articles
from generate_recent_news import GenerateRecentNews, Article, ImpactType
from progress_sink import ProgressSink

class TestIdentifyRelevantArticles(unittest.TestCase):
    """Test cases for the identify_relevant_articles function."""

    def setUp(self):
        """Set up test fixtures."""
        # Create a fresh mock for each test
        self.mock_ask_llm = MagicMock()
        self.patcher = patch('identification_of_relevant_articles.llm_client.ask_LLM', self.mock_ask_llm)
        self.patcher.start()

    def tearDown(self):
        """Clean up test fixtures."""
        self.patcher.stop()

    def test_identify_relevant_articles_success(self):
        """Test successful identification of relevant articles."""
        # Create a mock ProgressSink
        mock_sink = MagicMock(spec=ProgressSink)
        
        # Create a sample GenerateRecentNews object
        sample_recent_news = GenerateRecentNews(
            query="Bitcoin",
            query_meaning="Cryptocurrency Bitcoin",
            search_terms=["Bitcoin", "BTC", "cryptocurrency"],
            retrieved_urls=["https://example1.com", "https://example2.com", "https://example3.com", "https://example4.com"],
            parsed_urls={
                "https://example1.com": "Bitcoin price surged to $50,000 today.",
                "https://example2.com": "New regulations could impact Bitcoin trading.",
                "https://example3.com": "Bitcoin price surged to $50,000 today.",
                "https://example4.com": "New regulations could impact Bitcoin trading."
            },
            relevant_articles=[]
        )
        
        # Sample LLM response for mocking
        sample_llm_response = {
            'status_code': 200,
            'response_content': {
                'items': [
                    {
                        'article_number': '1',
                        'article_url': 'https://example1.com',
                        'impact_on_term_of_interest': 'Bitcoin price surged to $50,000, indicating strong market confidence.',
                        'impact_type': 'positive'
                    },
                    {
                        'article_number': '2',
                        'article_url': 'https://example2.com',
                        'impact_on_term_of_interest': 'New regulations could restrict Bitcoin trading, potentially reducing market activity.',
                        'impact_type': 'negative'
                    }
                ]
            }
        }

        # Configure the mock to return the response
        self.mock_ask_llm.return_value = sample_llm_response
        
        result = identify_relevant_articles(
            recent_news=sample_recent_news,
            sink=mock_sink
        )
        
        # Check that relevant_articles is a list
        self.assertIsInstance(result.relevant_articles, list)
        self.assertEqual(len(result.relevant_articles), 3)  
        
        # Check the response list
        response_list = result.relevant_articles[0]
        # Check that the response is a list
        self.assertIsInstance(response_list, list)
        self.assertGreater(len(response_list), 0)
        
        # Check each article in the response
        for article in response_list:
            # Check that it's an instance of Article
            self.assertIsInstance(article, Article)
            
            # Check that the article_url is in the parsed_urls keys
            self.assertIn(article.article_url, sample_recent_news.parsed_urls.keys())


    def test_identify_relevant_articles_llm_error(self):
        """Test handling of LLM errors."""
        # Create a mock ProgressSink
        mock_sink = MagicMock(spec=ProgressSink)
        
        # Create a sample GenerateRecentNews object
        sample_recent_news = GenerateRecentNews(
            query="Bitcoin",
            query_meaning="Cryptocurrency Bitcoin",
            search_terms=["Bitcoin", "BTC", "cryptocurrency"],
            retrieved_urls=["https://example1.com", "https://example2.com", "https://example3.com", "https://example4.com"],
            parsed_urls={
                "https://example1.com": "Bitcoin price surged to $50,000 today.",
                "https://example2.com": "New regulations could impact Bitcoin trading.",
                "https://example3.com": "Bitcoin price surged to $50,000 today.",
                "https://example4.com": "New regulations could impact Bitcoin trading."
            },
            relevant_articles=[]
        )
        
        # Sample LLM error response for mocking
        sample_llm_response = {
            'status_code': 500,
            'error': 'Internal server error'
        }

        # Configure the mock to return the error response
        self.mock_ask_llm.return_value = sample_llm_response
        
        result = identify_relevant_articles(
            recent_news=sample_recent_news,
            sink=mock_sink
        )
        
        # Check that relevant_articles is a list
        self.assertIsInstance(result.relevant_articles, list)
        self.assertEqual(len(result.relevant_articles), 3)
        
        # Check the response list
        response_list = result.relevant_articles[0]
        # Check that the response is a list
        self.assertIsInstance(response_list, list)
        # Verify that the list is empty for the error response
        self.assertEqual(len(response_list), 0)

    def test_identify_relevant_articles_no_urls(self):
        """Test that the function raises an error when no URLs are provided."""
        # Create a mock ProgressSink
        mock_sink = MagicMock(spec=ProgressSink)
        
        # Create a GenerateRecentNews object with no parsed URLs
        empty_recent_news = GenerateRecentNews(
            query="Bitcoin",
            query_meaning="Cryptocurrency Bitcoin",
            search_terms=["Bitcoin", "BTC", "cryptocurrency"],
            retrieved_urls=[],
            parsed_urls={},
            relevant_articles=[]
        )
        
        # Assert that the function raises a ValueError
        with self.assertRaises(ValueError) as context:
            identify_relevant_articles(
                recent_news=empty_recent_news,
                sink=mock_sink
            )
        
        # Check the error message
        self.assertEqual(str(context.exception), "No URLs have been parsed")


if __name__ == '__main__':
    unittest.main() 