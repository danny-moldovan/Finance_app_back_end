from abc import ABC, abstractmethod
from duckduckgo_search import DDGS
from cache import *
from utils import *
from typing import *
from progress_sink import *


NEWS_RESULT_COUNT = 10


class WebSearchClient(ABC):
    """Abstract base class for a websearch client."""     
    
    @abstractmethod
    def __init__(self):
        """Constructor to initialize the websearch client."""
        pass

    @abstractmethod
    def search_web(self, search_term):
        """Method to search a search term on the web."""
        pass


class DuckDuckGoClient(WebSearchClient):
    """Concrete implementation of WebSearchClient for DuckDuckGo."""

    def __init__(self):
        """Initializes the client."""
        self.client = DDGS()

    @retry_on_exceeding_rate_limit(max_retries = 10, base_delay = 3.0, backoff_factor = 2.0)
    def search_web(self, search_term, rate_limiter = rate_limiter_search_requests):
        """Searches a search term on the web."""

        try:
            key = "Search results for: {}".format(search_term)
            cached_result = cache.get(key, ["No cache entry found"])
            #log.info('Searching for key in the cache: {}, found: {}\n'.format(key, cached_result))
    
            if cached_result != ["No cache entry found"]:
                log.info('Cache hit for {}\n'.format(key))
                return {'status_code': 200, 'search_results': cached_result}
            else:
                log.info('Searching the web for {}\n'.format(search_term))
    
                rate_limiter.acquire()
                
                search_results = self.client.news(
                    keywords = search_term, 
                    region = "us-en", #or "wt-wt" ?
                    timelimit = "d", #results from today only
                    max_results = NEWS_RESULT_COUNT
                )
    
                search_results_urls = [n['url'] for n in search_results]
                #log.info('Search results found for {}: {}\n'.format(search_term, search_results_urls))
    
                previously_stored_search_results = cache.get(key, ["No cache entry found"])
                if previously_stored_search_results != ["No cache entry found"]:
                    log.info('Search results already stored in the cache for the same search query {}\n'.format(search_term))
                    return {'status_code': 200, 'search_results': previously_stored_search_results}
                else:
                    cache.set(key, search_results_urls, expire = TTL)
                    #log.info('Cache entry set for {}\n'.format(key))
                    return {'status_code': 200, 'search_results': search_results_urls}
    
        except Exception as e:
                log.info('An exception ocurred during searching the web for {}: {}\n'.format(search_term, e))
                return {'status_code': getattr(e, 'status_code', 500), 'search_results': []}


websearch_client = DuckDuckGoClient()