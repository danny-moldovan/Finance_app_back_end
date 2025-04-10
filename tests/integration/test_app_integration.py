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
        # Get the response data and split it into lines
        response_data = response.get_data().decode('utf-8')
        for line in response_data.split('\n'):
            if not line.strip():  # Skip empty lines
                continue
            
            print(line)
            message = json.loads(line)
            message1 = json.loads(message)
            print('Message:', message1)
            if message1['message_type'] == 'final':
                found_final_message = True
                final_message = message1['message']
                assert isinstance(final_message, list) and len(final_message) >= 1
                assert len(final_message[0]) >= 300
                break
        
        assert found_final_message, "No final message found in the response stream"

    def test_generate_recent_news_endpoint_with_missing_query(self, client):
        """Test news generation endpoint with missing query parameter."""
        response = client.post('/generate_recent_news', json={})
        assert response.status_code == 400
        data = json.loads(response.data)
        assert 'error' in data


