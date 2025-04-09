import os
from urllib.parse import quote_plus

from bs4 import BeautifulSoup
import requests
from dotenv import load_dotenv

from cache import cache, TTL
from generate_recent_news import GenerateRecentNews
from progress_sink import ProgressSink
from utils import log, get_and_log_current_time, log_processing_duration, run_multiple_with_limited_time, convert_to_dictionary

load_dotenv()

MAX_TIME_WEBPAGE_CRAWLING = 5


def _crawl_url_using_crawlbase(url: str) -> dict[str, str]:
    """
    Crawls a URL using the Crawlbase API service.
    
    Args:
        url (str): The URL to crawl
        
    Returns:
        dict[str, str]: A dictionary containing the status code and content of the crawled page
    """

    try:
        api_url = f"https://api.crawlbase.com/?token={os.environ.get('CRAWLBASE_API')}&url={quote_plus(url)}"
        response = requests.get(url=api_url, timeout=MAX_TIME_WEBPAGE_CRAWLING)

        if response.status_code == 200:
            log.info(msg=f"Crawled URL {url} successfully using Crawlbase\n")

        response.raise_for_status()
        return {'status_code': response.status_code, 'content': response.text.strip()}

    except requests.exceptions.RequestException as e:
        status_code = getattr(e.response, 'status_code', 500) if hasattr(e, 'response') else 500
        log.info(msg=f"Error crawling URL {url} using Crawlbase: {str(e)}\n")
        return {'status_code': status_code, 'content': ''}


def _extract_text_from_url(url: str) -> dict[str, str]:
    """
    Extracts text content from a URL using the requests library.
    
    Args:
        url (str): The URL to extract text from
        
    Returns:
        dict[str, str]: A dictionary containing the status code and content of the page
    """

    try:
        response = requests.get(url=url, timeout=MAX_TIME_WEBPAGE_CRAWLING)
        response.raise_for_status()
        
        #if response.status_code == 200:
        #    log.info(msg=f"Crawled URL {url} successfully\n")

        return {'status_code': response.status_code, 'content': response.text.strip()}

    except requests.exceptions.RequestException as e:
        return _crawl_url_using_crawlbase(url)

        #status_code = getattr(e.response, 'status_code', 500) if hasattr(e, 'response') else 500
        #log.info(msg=f"Error extracting text from URL {url}: {str(e)}")
        #return {'status_code': status_code, 'content': ''}


def _parse_text_from_url(text: str) -> str:
    """
    Parses HTML text to extract clean paragraph content.
    
    Args:
        text (str): The HTML text to parse
        
    Returns:
        str: Cleaned text content with duplicate paragraphs removed. Returns empty string if input is empty, None, or contains only whitespace.
    """

    if not text or not text.strip():
        return ''
        
    soup = BeautifulSoup(text, 'html.parser')
    paragraphs = soup.find_all('p')
    
    # Use a set comprehension for deduplication and cleaning
    unique_paragraphs = {
        ' '.join(p.get_text().split())
        for p in paragraphs
    }
    
    return ' '.join(unique_paragraphs).strip()


def _processWebpage(url: str) -> dict[str, str]:
    """
    Processes a webpage by extracting and parsing its content
    
    Args:
        url (str): The URL to process
        
    Returns:
        dict[str, str]: A dictionary containing the status code and processed content
    """
    key = f"Crawled content of the website: {url}"
    cached_result = cache.get(key=key, default=["No cache entry found"])

    if cached_result != ["No cache entry found"]:
        return {'status_code': 200, 'content': cached_result}

    try:
        extracted_text = _extract_text_from_url(url=url)
        
        if extracted_text['status_code'] == 200:
            parsed_text = _parse_text_from_url(text=extracted_text['content'])
            cache.set(key=key, value=parsed_text, expire=TTL)
            return {'status_code': 200, 'content': parsed_text}
            
        cache.set(key=key, value='', expire=TTL)
        return {'status_code': extracted_text['status_code'], 'content': ''}
        
    except Exception as e:
        cache.set(key=key, value='', expire=TTL)
        return {'status_code': getattr(e, 'status_code', 500), 'content': ''}


def _set_entry_for_timed_out_crawls(retrieved_urls: list[str], crawling_results: dict[str, str]) -> dict[str, str]:
    """
    Sets an empty entry into the crawling results dictionary and into the cache for URLs for which the crawling timed out
    
    Args:
        retrieved_urls (list[str]): A list of URLs
        crawling_results (dict[str, str]): A dictionary containing for each URL the extracted text content
    
    Returns:
        dict[str, str]: The crawling results dictionary with empty entries for timed out URLs
    """
    
    timed_out_urls = [
        url for url in retrieved_urls
        if cache.get(key=f"Crawled content of the website: {url}", default=["No cache entry found"]) == ["No cache entry found"]
    ]
    
    for url in timed_out_urls:
        cache.set(key=f"Crawled content of the website: {url}", value='', expire=TTL)
        crawling_results[url] = ''
    
    if timed_out_urls:
        log.info(msg=f'The crawling timed out for {len(timed_out_urls)} URLs\n')
    
    return crawling_results


def _get_urls_that_could_be_parsed(crawling_results: dict[str, str], sink: ProgressSink) -> dict[str, str]:
    """
    Filters URLs to keep only those that could be successfully parsed.
    
    Args:
        crawling_results (dict[str, str]): A dictionary containing for each URL the extracted text content
        sink (ProgressSink): A message sink to which progress messages are sent
    
    Returns:
        dict[str, str]: A dictionary containing only the URLs that could be parsed
    """
    
    parsed_urls = {url: content for url, content in crawling_results.items() if len(content) > 0}
    
    total_urls = len(crawling_results)
    parsed_count = len(parsed_urls)
    message = f'{parsed_count} URLs out of {total_urls} could be parsed'
    
    log.info(msg=message + '\n')
    sink.send(message=message)

    return parsed_urls


def perform_crawling(recent_news: GenerateRecentNews, sink: ProgressSink) -> GenerateRecentNews:
    """
    Perform crawling of the retrieved URLs
    
    Args:
        recent_news (GenerateRecentNews): The news generation request, having the retrieved_urls field populated
        sink (ProgressSink): A message sink to which progress messages are sent
    
    Returns:
        GenerateRecentNews: A new object with crawled URLs
    """

    if not recent_news.retrieved_urls:
        raise Exception("No URLs have been returned by the web search")
        
    timestamp_start = get_and_log_current_time(
        message=f'The crawling for {recent_news.query} started at',
        sink=sink
    )   
    
    # Filter out MSN URLs and process the rest
    urls_to_process = [url for url in recent_news.retrieved_urls if 'www.msn.com' not in url]
    
    def wrapper(crawling_function):
        return lambda url, results: results.append({url: crawling_function(url=url)['content']})
        
    crawling_results = convert_to_dictionary(
        key_value_list=run_multiple_with_limited_time(
            func=wrapper(_processWebpage),
            args=urls_to_process,
            max_time=MAX_TIME_WEBPAGE_CRAWLING
        )
    )
    
    crawling_results = _set_entry_for_timed_out_crawls(
        retrieved_urls=recent_news.retrieved_urls,
        crawling_results=crawling_results
    )
    
    parsed_urls = _get_urls_that_could_be_parsed(
        crawling_results=crawling_results,
        sink=sink
    )
    
    timestamp_end = get_and_log_current_time(
        message=f'The crawling for {recent_news.query} finished at',
        sink=sink
    )

    log_processing_duration(
        timestamp_start=timestamp_start,
        timestamp_end=timestamp_end,
        message=f'The crawling for {recent_news.query}',
        sink=sink
    )
    
    return GenerateRecentNews(
        query=recent_news.query,
        query_meaning=recent_news.query_meaning,
        search_terms=recent_news.search_terms,
        retrieved_urls=recent_news.retrieved_urls,
        parsed_urls=parsed_urls
    )
