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

    
class TestBatchProcessingEndpoints:
    """Test suite for batch processing functionality."""

    def test_process_batch_sequential(self, client):
        """Test sequential batch processing through the endpoint."""
        response = client.post('/generate_recent_news_batch', 
                            json={
                                'input_filename': 'test_cases.txt',
                                'n_rows': '1',
                                'in_parallel': False
                            })
        
        found_final_message = False
        for line in response.response:
            if not line.strip():  # Skip empty lines
                continue

            message = json.loads(line)
            message1 = json.loads(message)

            if 'number_of_outputs' in message1['message']:
                assert 'number_of_outputs' in message1['message'] and message1['message']['number_of_outputs'] == 1

            if message1['message_type'] == 'final':
                found_final_message = True
                assert 'status_code' in message1['message'] and message1['message']['status_code'] == 200
                break
        
        assert found_final_message, "No final message found in the response stream"

    def test_process_batch_parallel(self, client):
        """Test parallel batch processing through the endpoint."""
        response = client.post('/generate_recent_news_batch', 
                            json={
                                'input_filename': 'test_cases.txt',
                                'n_rows': '1',
                                'in_parallel': True
                            })
        
        found_final_message = False
        for line in response.response:
            message = json.loads(line)
            message1 = json.loads(message)

            if 'number_of_outputs' in message1['message']:
                assert 'number_of_outputs' in message1['message'] and message1['message']['number_of_outputs'] == 1

            if message1['message_type'] == 'final':
                found_final_message = True
                assert 'status_code' in message1['message'] and message1['message']['status_code'] == 200
                break
        
        assert found_final_message, "No final message found in the response stream"

    def test_generate_recent_news_batch_endpoint_with_missing_filename(self, client):
        """Test batch news generation endpoint with missing filename."""
        response = client.post('/generate_recent_news_batch', json={})
        assert response.status_code == 400
        data = json.loads(response.data)
        assert 'error' in data