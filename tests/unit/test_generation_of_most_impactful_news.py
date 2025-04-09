import unittest
from unittest.mock import MagicMock, patch
import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from generate_recent_news import GenerateRecentNews, News, Article, ImpactType
from generation_of_most_impactful_news import generate_most_impactful_news
from progress_sink import ProgressSink
from llm_client import llm_client


class TestGenerateMostImpactfulNews(unittest.TestCase):
    """Test cases for the generate_most_impactful_news function."""

    def test_successful_generation(self):
        """Test successful generation of most impactful news."""

        sink = MagicMock(spec=ProgressSink)
        sample_article1 = Article(
            article_number='1',
            article_url='https://example.com/article1',
            impact_summary_on_query='Positive impact on Bitcoin',
            impact_type_on_query=ImpactType.POSITIVE
        )
        sample_article2 = Article(
            article_number='2',
            article_url='https://example.com/article2',
            impact_summary_on_query='Positive impact on Bitcoin adoption',
            impact_type_on_query=ImpactType.POSITIVE
        )
        sample_parsed_urls = {
            'https://example.com/article1': 'Article 1 text content',
            'https://example.com/article2': 'Article 2 text content'
        }
        sample_relevant_articles = [[sample_article1], [sample_article2]]
        sample_llm_response = {
            'status_code': 200,
            'response_content': {
                'items': [
                    {
                        'news': 'Bitcoin price increased',
                        'most_relevant_url': 'https://example.com/article1',
                        'impact_of_news_on_term_of_interest': 'Positive impact on Bitcoin price',
                        'impact_type_of_news': 'positive'
                    },
                    {
                        'news': 'Bitcoin adoption growing',
                        'most_relevant_url': 'https://example.com/article2',
                        'impact_of_news_on_term_of_interest': 'Positive impact on Bitcoin adoption',
                        'impact_type_of_news': 'positive'
                    }
                ]
            }
        }

        recent_news = GenerateRecentNews(
            query='Bitcoin',
            query_meaning='Cryptocurrency',
            search_terms=['Bitcoin', 'BTC'],
            retrieved_urls=['https://example.com/article1', 'https://example.com/article2'],
            parsed_urls=sample_parsed_urls,
            relevant_articles=sample_relevant_articles,
            most_impactful_news=[]
        )

        with patch('generation_of_most_impactful_news.llm_client.ask_LLM') as mock_ask_llm:
            mock_ask_llm.return_value = sample_llm_response

            result = generate_most_impactful_news(recent_news, sink)

            self.assertIsInstance(result, GenerateRecentNews)
            self.assertEqual(len(result.most_impactful_news), 2)
            
            # Get all article URLs from relevant_articles
            relevant_article_urls = [article.article_url for sublist in sample_relevant_articles for article in sublist]
            
            for news in result.most_impactful_news:
                self.assertIsInstance(news, News)
                self.assertIn(news.most_relevant_url, relevant_article_urls)
            mock_ask_llm.assert_called_once()


    def test_no_relevant_articles(self):
        """Test handling of case with no relevant articles."""

        sink = MagicMock(spec=ProgressSink)
        recent_news = GenerateRecentNews(
            query='Bitcoin',
            query_meaning='Cryptocurrency',
            search_terms=['Bitcoin', 'BTC'],
            retrieved_urls=[],
            parsed_urls={},
            relevant_articles=[],
            most_impactful_news=[]
        )

        with self.assertRaises(ValueError):
            generate_most_impactful_news(recent_news, sink)


    def test_llm_error(self):
        """Test handling of LLM error response."""

        sink = MagicMock(spec=ProgressSink)
        sample_article = Article(
            article_number='1',
            article_url='https://example.com/article1',
            impact_summary_on_query='Positive impact on Bitcoin',
            impact_type_on_query=ImpactType.POSITIVE
        )
        sample_parsed_urls = {
            'https://example.com/article1': 'Article text content'
        }
        sample_relevant_articles = [[sample_article]]

        recent_news = GenerateRecentNews(
            query='Bitcoin',
            query_meaning='Cryptocurrency',
            search_terms=['Bitcoin', 'BTC'],
            retrieved_urls=['https://example.com/article1'],
            parsed_urls=sample_parsed_urls,
            relevant_articles=sample_relevant_articles,
            most_impactful_news=[]
        )

        with patch('generation_of_most_impactful_news.llm_client.ask_LLM') as mock_ask_llm:
            mock_ask_llm.return_value = {'status_code': 500}

            with self.assertRaises(Exception):
                generate_most_impactful_news(recent_news, sink)


    def test_empty_llm_response(self):
        """Test handling of empty LLM response."""

        sink = MagicMock(spec=ProgressSink)
        sample_article = Article(
            article_number='1',
            article_url='https://example.com/article1',
            impact_summary_on_query='Positive impact on Bitcoin',
            impact_type_on_query=ImpactType.POSITIVE
        )
        sample_parsed_urls = {
            'https://example.com/article1': 'Article text content'
        }
        sample_relevant_articles = [[sample_article]]

        recent_news = GenerateRecentNews(
            query='Bitcoin',
            query_meaning='Cryptocurrency',
            search_terms=['Bitcoin', 'BTC'],
            retrieved_urls=['https://example.com/article1'],
            parsed_urls=sample_parsed_urls,
            relevant_articles=sample_relevant_articles,
            most_impactful_news=[]
        )

        with patch('generation_of_most_impactful_news.llm_client.ask_LLM') as mock_ask_llm:
            mock_ask_llm.return_value = {
                'status_code': 200,
                'response_content': {}
            }

            result = generate_most_impactful_news(recent_news, sink)

            self.assertIsInstance(result, GenerateRecentNews)
            self.assertEqual(len(result.most_impactful_news), 0)


if __name__ == '__main__':
    unittest.main() 