from cache import cache, TTL
from generate_recent_news import GenerateRecentNews
from progress_sink import ProgressSink
from utils import log, get_and_log_current_time, log_processing_duration, run_multiple_with_limited_time, convert_to_dictionary
from websearch_client import websearch_client


MAX_TIME_WEBSEARCH_PER_SEARCH_TERM = None


def _set_entry_for_timed_out_searches(search_terms: list[str], search_results: dict[str, list[str]]) -> dict[str, list[str]]:
    """
    Sets an empty entry into the result dictionary and into the cache for search terms for which the web search timed out
    
    Args:
        search_terms (list[str]): A list of search terms
        search_results (dict[str, list[str]]): A dictionary containing for each search term the list of retrieved URLs
    
    Returns:
        dict[str, list[str]]: The search_results dictionary, into which an empty list was set as a result for each search that timed out
    """
    
    for s in search_terms:   
        key = "Search results for: {}".format(s)
        if cache.get(key=key, default=["No cache entry found"]) == ["No cache entry found"]:
            cache.set(key=key, value=[], expire=TTL)
            #log.info('Cache entry set (after the search was done) for {}: {}\n'.format(s, []))
            search_results[s] = []

    return search_results
    

def _log_search_results(search_results: dict[str, list[str]]) -> None:
    """
    Logs the count of search results for each search term in sorted order.
    
    Args:
        search_results (dict[str, list[str]]): A dictionary containing for each search term the list of retrieved URLs

    Returns:
        None    
    """
    
    sorted_keys = sorted(list(search_results.keys()))
    search_results_counts = [len(search_results[key]) for key in sorted_keys]

    log.info(msg='Search results: {}\n'.format(search_results_counts))


def _aggregate_search_results(search_results: dict[str, list[str]]) -> list[str]:
    """
    Aggregates and deduplicates search results for multiple search terms
    
    Args:
        search_results (dict[str, list[str]]): A dictionary containing for each search term the list of retrieved URLs
    
    Returns:
        list[str]: A sorted list containing the aggregated and deduplicated search results
    """
    
    aggregated_search_results = set(url for urls in search_results.values() for url in urls)
    return sorted(list(aggregated_search_results))


def perform_web_search(recent_news: GenerateRecentNews, sink: ProgressSink) -> GenerateRecentNews:
    """
    Perform websearch of the generated search terms
    
    Args:
        recent_news (GenerateRecentNews): The news generation request, having the search_terms field populated
        sink (ProgressSink): A message sink to which progress messages are sent
    
    Returns:
        GenerateRecentNews: A new object with retrieved URLs based on the search terms
    
    Raises:
        ValueError: If search_terms is empty
    """

    timestamp_start = get_and_log_current_time(message=f'The web search for {recent_news.query} started at', sink=sink)   
    
    if len(recent_news.search_terms) == 0:
        raise Exception("Search terms have not been generated")
    
    def wrapper(search_function):
        return lambda search_term, results: results.append({search_term: search_function(search_term)['search_results']})
    
    search_results = list(run_multiple_with_limited_time(
        func=wrapper(websearch_client.search_web),
        args=recent_news.search_terms,
        max_time=MAX_TIME_WEBSEARCH_PER_SEARCH_TERM
    ))
    search_results = convert_to_dictionary(key_value_list=search_results)  
    search_results = _set_entry_for_timed_out_searches(
        search_terms=recent_news.search_terms,
        search_results=search_results
    )
    _log_search_results(search_results=search_results)

    aggregated_results = _aggregate_search_results(search_results=search_results)
    result_count = len(aggregated_results)
    sink.send(message=f'Found {result_count} search results')
    log.info(msg=f'Found {result_count} search results\n')
    
    timestamp_end = get_and_log_current_time(message=f'The web search for {recent_news.query} finished at', sink=sink)
    log_processing_duration(
        timestamp_start=timestamp_start,
        timestamp_end=timestamp_end,
        message=f'The web search for {recent_news.query}',
        sink=sink
    )
    
    return GenerateRecentNews(
        query=recent_news.query,
        query_meaning=recent_news.query_meaning,
        search_terms=recent_news.search_terms,
        retrieved_urls=aggregated_results
    )
