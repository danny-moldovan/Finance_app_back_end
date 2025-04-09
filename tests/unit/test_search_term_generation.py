import os
import sys
import unittest
from multiprocessing import Queue
from unittest.mock import patch

# Get the absolute path to the back_end directory
back_end_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if back_end_path not in sys.path:
    sys.path.insert(0, back_end_path)

from search_term_generation import generate_search_terms
from progress_sink import ProgressSink
from generate_recent_news import GenerateRecentNews

class TestSearchTermGeneration(unittest.TestCase):
    def setUp(self):
        self.queue = Queue()
        self.sink = ProgressSink(self.queue)
        
    def test_generate_search_terms_success(self):
        # Mock the LLM response
        mock_llm_response = {
            'status_code': 200,
            'response_content': {
                'query_meaning': 'Test query meaning',
                'list_search_terms': ['term1', 'term2'],
                'list_search_terms_tracked_index': ['index1', 'index2'],
                'list_search_terms_country_or_region': ['region1', 'region2'],
                'list_search_terms_industries_and_sectors': ['industry1', 'industry2'],
                'list_search_terms_related_terms': ['related1', 'related2']
            }
        }
        
        with patch('search_term_generation.llm_client.ask_LLM', return_value=mock_llm_response):
            result = generate_search_terms('test query', self.sink)
            
            # Verify the result is a GenerateRecentNews object
            self.assertIsInstance(result, GenerateRecentNews)
            
            # Verify the query and query_meaning
            self.assertEqual(result.query, 'test query')
            self.assertEqual(result.query_meaning, 'Test query meaning')
            
            # Verify search terms include all expected terms
            expected_terms = {'term1', 'term2', 'index1', 'index2', 'region1', 'region2', 
                            'industry1', 'industry2', 'related1', 'related2', 'test query'}
            self.assertEqual(set(result.search_terms), expected_terms)
            
    def test_generate_search_terms_llm_error(self):
        # Mock the LLM response with an error
        mock_llm_response = {
            'status_code': 500,
            'response_content': {}
        }
        
        with patch('search_term_generation.llm_client.ask_LLM', return_value=mock_llm_response):
            with self.assertRaises(Exception) as context:
                generate_search_terms('test query', self.sink)
            
            self.assertIn('An exception occurred during the LLM call', str(context.exception))
            
    def test_generate_search_terms_empty_response(self):
        # Mock the LLM response with empty content
        mock_llm_response = {
            'status_code': 200,
            'response_content': {
                'query_meaning': '',
                'list_search_terms': [],
                'list_search_terms_tracked_index': [],
                'list_search_terms_country_or_region': [],
                'list_search_terms_industries_and_sectors': [],
                'list_search_terms_related_terms': []
            }
        }
        
        with patch('search_term_generation.llm_client.ask_LLM', return_value=mock_llm_response):
            result = generate_search_terms('test query', self.sink)
            
            # Verify the result contains at least the original query
            self.assertEqual(result.search_terms, ['test query'])
            
    def test_generate_search_terms_duplicate_terms(self):
        # Mock the LLM response with duplicate terms
        mock_llm_response = {
            'status_code': 200,
            'response_content': {
                'query_meaning': 'Test query meaning',
                'list_search_terms': ['term1', 'term1'],
                'list_search_terms_tracked_index': ['term1', 'index1'],
                'list_search_terms_country_or_region': ['region1', 'region1'],
                'list_search_terms_industries_and_sectors': ['industry1', 'industry1'],
                'list_search_terms_related_terms': ['related1', 'related1']
            }
        }
        
        with patch('search_term_generation.llm_client.ask_LLM', return_value=mock_llm_response):
            result = generate_search_terms('test query', self.sink)
            
            # Verify duplicate terms are removed
            expected_terms = {'term1', 'index1', 'region1', 'industry1', 'related1', 'test query'}
            self.assertEqual(set(result.search_terms), expected_terms)

    def test_generate_search_terms_empty_query(self):
        # Mock the LLM response for empty query
        mock_llm_response = {
            'status_code': 200,
            'response_content': {
                'query_meaning': '',
                'list_search_terms': [],
                'list_search_terms_tracked_index': [],
                'list_search_terms_country_or_region': [],
                'list_search_terms_industries_and_sectors': [],
                'list_search_terms_related_terms': []
            }
        }
        
        with patch('search_term_generation.llm_client.ask_LLM', return_value=mock_llm_response):
            result = generate_search_terms('', self.sink)
            
            # Verify the result contains only the empty query
            self.assertEqual(result.search_terms, [''])
            self.assertEqual(result.query, '')
            self.assertEqual(result.query_meaning, '')

if __name__ == '__main__':
    unittest.main() 