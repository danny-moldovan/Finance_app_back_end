from google import genai
from dotenv import load_dotenv
import os
from abc import ABC, abstractmethod
import requests
import json
import json5
from cache import *
from utils import *
from typing import *

load_dotenv()


class LLM_client(ABC):
    """Abstract base class for an LLM client."""     
    
    @abstractmethod
    def __init__(self):
        """Constructor to initialize the LLM client."""
        pass

    @abstractmethod
    def ask_LLM(self, prompt):
        """Method to send a prompt to the LLM and return the response."""
        pass


def clean_text(text: str) -> str:
    """
    Cleans and prepares text for JSON parsing by handling various quote types and formatting.
    
    Args:
        text (str): The text to clean
        
    Returns:
        str: The cleaned text ready for JSON parsing
    """
    # Remove markdown code block markers if present
    if text.startswith('```json'):
        text = text[7:]
    if text.startswith('```'):
        text = text[3:]
    if text.endswith('```'):
        text = text[:-3]
    
    # Clean up the text
    text = text.strip()
    text = text.replace('`', '')
    
    # Handle all types of quotes and apostrophes
    quote_replacements = {
        '\u2018': "'",  # Left single quote
        '\u2019': "'",  # Right single quote
        '\u201c': '"',  # Left double quote
        '\u201d': '"',  # Right double quote
        '\u201a': "'",  # Single low-9 quote
        '\u201b': "'",  # Single high-reversed-9 quote
        '\u201e': '"',  # Double low-9 quote
        '\u201f': '"',  # Double high-reversed-9 quote
        '\u2032': "'",  # Prime (minutes, feet)
        '\u2033': '"',  # Double prime (seconds, inches)
        '\u2035': "'",  # Reversed prime
        '\u2036': '"',  # Reversed double prime
        '\u2039': "'",  # Single left-pointing angle quote
        '\u203a': "'",  # Single right-pointing angle quote
        '\u275b': '"',  # Heavy single turned comma quote
        '\u275c': '"',  # Heavy single comma quote
        '\u275d': '"',  # Heavy double turned comma quote
        '\u275e': '"',  # Heavy double comma quote
    }
    
    for curly, straight in quote_replacements.items():
        text = text.replace(curly, straight)
    
    # Handle apostrophes in possessives and contractions
    text = text.replace("'s", "\\'s")
    text = text.replace("'t", "\\'t")
    text = text.replace("'m", "\\'m")
    text = text.replace("'re", "\\'re")
    text = text.replace("'ve", "\\'ve")
    text = text.replace("'ll", "\\'ll")
    text = text.replace("'d", "\\'d")
    
    return text


class Gemini_client(LLM_client):
    """Concrete implementation of LLM_client for Google's Gemini model."""

    def __init__(self, model_name):
        """Initializes the Gemini client with an API key."""
        self.model_name = model_name
        self.client = genai.Client(api_key = os.getenv('GEMINI_API_KEY'), http_options = {'api_version' : 'v1alpha'})

    @retry_on_exceeding_rate_limit(max_retries = 10, base_delay = 3.0, backoff_factor = 2.0)
    def ask_LLM(self, prompt, rate_limiter = rate_limiter_llm_calls, cache_prefix = ''):
        """
        Sends a prompt to Gemini and returns the response.
        
        Args:
            prompt: The prompt to send to the LLM
            rate_limiter: Rate limiter instance for controlling API calls
            cache_prefix: Optional prefix for cache key
            
        Returns:
            dict: Dictionary containing status code and response content
        """
        try:
            # Generate cache key
            key = f"LLM answer {cache_prefix} for the prompt: {prompt}" if cache_prefix else f"LLM answer for the prompt: {prompt}"
            
            # Check cache first
            cached_result = cache.get(key)
            if cached_result is not None:
                log.info(f'Cache hit for LLM call for {cache_prefix}\n')
                return {'status_code': 200, 'response_content': cached_result}
            
            # Acquire rate limiter before making API call
            rate_limiter.acquire()
            
            # Make API call
            response = self.client.models.generate_content(
                model = self.model_name,
                contents = prompt
            )
            
            # Get and clean response text
            response_text = response.candidates[0].content.parts[0].text
            log.info(f'LLM response text for {cache_prefix}: {response_text}\n')
            
            # Clean and parse response
            response_text = clean_text(response_text)
            try:
                response_content = json5.loads(response_text)
            except Exception as e:
                log.error(f'Failed to parse LLM response as JSON: {str(e)}\nResponse text: {response_text}')
                raise
            
            # Cache successful response
            cache.set(key, response_content, expire = TTL)
            log.info(f'Cache entry set for LLM call: {cache_prefix} of length {len(json.dumps(response_content))}\n')
            
            return {'status_code': 200, 'response_content': response_content}
            
        except Exception as e:
            log.error(f'An exception occurred during the LLM call for {cache_prefix}: {str(e)}\n')
            return {'status_code': getattr(e, 'status_code', 500), 'response_content': ''}
            

llm_client = Gemini_client("gemini-2.0-flash-thinking-exp")