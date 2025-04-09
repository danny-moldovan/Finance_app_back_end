"""Integration tests for the Flask application endpoints and core functionality.

This module contains integration tests that verify the behavior of the Flask application,
including its endpoints and core functionality. The tests cover:
- Health check endpoints
- News generation endpoints
- Batch processing functionality
"""

import pytest
import json
import os
from unittest.mock import patch, MagicMock
from app import app
from cache import cache


@pytest.fixture
def client():
    """Create a test client for the Flask application.
    
    Returns:
        FlaskClient: A test client instance for making requests to the application.
    """
    # Configure app for testing
    app.config['TESTING'] = True
    app.config['SERVER_NAME'] = 'localhost'
    
    # Use test_client() as a context manager to ensure proper cleanup
    with app.test_client() as client:
        # Push an application context
        with app.app_context():
            yield client
            # Context is automatically cleaned up after the yield


@pytest.fixture(autouse=True)
def setup_and_teardown():
    """Setup and teardown for each test."""
    # Setup
    cache.clear()
    
    yield
    
    # Teardown
    cache.clear()


class TestHealthCheckEndpoints:
    """Test suite for health check endpoints."""

    def test_health_check_endpoint_with_valid_input(self, client):
        """Test health check endpoint with valid input."""
        response = client.post('/health_check', json={'query': 'test query'})
        assert response.status_code == 200
        data = json.loads(response.data)
        assert 'message' in data
        assert 'test query' in data['message']

    def test_health_check_endpoint_with_missing_query(self, client):
        """Test health check endpoint with missing query parameter."""
        response = client.post('/health_check', json={})
        assert response.status_code == 400
        data = json.loads(response.data)
        assert 'error' in data

    def test_health_check_streaming_endpoint_with_valid_input(self, client):
        """Test streaming health check endpoint with valid input."""
        response = client.post('/health_check_streaming', json={'query': 'test query'})
        assert response.status_code == 200
        response_data = list(response.response)
        assert len(response_data) == 3
        assert b'Request' in response_data[0]
        assert b'test query' in response_data[1]
        assert b'was successful!' in response_data[2]

    def test_health_check_streaming_endpoint_with_missing_query(self, client):
        """Test streaming health check endpoint with missing query parameter."""
        response = client.post('/health_check_streaming', json={})
        assert response.status_code == 400
        data = json.loads(response.data)
        assert 'error' in data


class TestNewsGenerationEndpoints:
    """Test suite for news generation endpoints."""

    def test_generate_recent_news_endpoint_with_valid_input(self, client):
        """Test news generation endpoint with valid input."""
        response = client.post('/generate_recent_news', json={'query': 'US stocks'})
        assert response.status_code == 200
        
        found_final_message = False
        for line in response.response:
            message = json.loads(line)
            if message['message_type'] == 'final':
                found_final_message = True
                final_message = message['message']
                print('Final message: ', final_message, '\n')
                assert len(final_message) >= 1 and len(final_message[0])>= 300
                break
        
        print('Found final message: ', found_final_message)
        assert found_final_message, "No final message found in the response stream"

    def test_generate_recent_news_endpoint_with_missing_query(self, client):
        """Test news generation endpoint with missing query parameter."""
        response = client.post('/generate_recent_news', json={})
        assert response.status_code == 400
        data = json.loads(response.data)
        assert 'error' in data


class TestBatchProcessingEndpoints:
    """Test suite for batch processing functionality."""

    def test_process_batch_sequential(self, client):
        """Test sequential batch processing through the endpoint."""
        response = client.post('/generate_recent_news_batch', 
                            json={
                                'input_filename': 'test_cases.txt',
                                'n_rows': 2,
                                'in_parallel': False
                            })
        assert response.status_code == 200
        
        found_final_message = False
        for line in response.response:
            message = json.loads(line)

            if 'number_of_outputs' in message['message']:
                assert message['message']['number_of_outputs'] == 2

            if message['message_type'] == 'final':
                found_final_message = True
                assert message['message']['status_code'] == 200
                break
        
        assert found_final_message, "No final message found in the response stream"

    def test_process_batch_parallel(self, client):
        """Test parallel batch processing through the endpoint."""
        response = client.post('/generate_recent_news_batch', 
                            json={
                                'input_filename': 'test_cases.txt',
                                'n_rows': 2,
                                'in_parallel': True
                            })
        assert response.status_code == 200
        
        found_final_message = False
        for data in response.response:
            message = json.loads(data)

            if 'number_of_outputs' in message['message']:
                assert message['message']['number_of_outputs'] == 2

            if message['message_type'] == 'final':
                found_final_message = True
                assert message['message']['status_code'] == 200
                break
        
        assert found_final_message, "No final message found in the response stream"

    def test_generate_recent_news_batch_endpoint_with_missing_filename(self, client):
        """Test batch news generation endpoint with missing filename."""
        response = client.post('/generate_recent_news_batch', json={})
        assert response.status_code == 400
        data = json.loads(response.data)
        assert 'error' in data