from generate_recent_news import GenerateRecentNews
from llm_client import llm_client
from progress_sink import ProgressSink
from utils import log, get_and_log_current_time, log_processing_duration


SEARCH_TERM_GENERATION_PROMPT_TEMPLATE = '''Please perform the following steps:
Step 1: If the TERM OF INTEREST is a symbol of a financial instrument (for example stocks, bonds or currencies or currency pairs)
then please identify its explicit name. Please keep it very concise.

Step 2: Generate at least {0} search queries that could be used to find recent financial news on the web
about the original TERM OF INTEREST 

Step 3: If the TERM OF INTEREST is an ETF that tracks any index, please identify it. For example the ETF SPY tracks the S&P 500 Index.

Step 4: Generate at least {0} search queries that could be used to find recent financial news on the web
about the tracked index (if any, otherwise leave empty). 

Step 5: Identify the most relevant country or region (can be 'global') to the TERM OF INTEREST. 
For example for SPY the most relevant country is 'US'.
For example VT refers to the region 'global'.

Step 6: Generate at least {0} search queries that could be used to find recent financial news on the web
about the countries or regions identified at step 5. 

Step 7: Identify the most relevant industries and sectors to the TERM OF INTEREST.
For example the ETF SPY refers to all indsutries.
For example the ETF IYW refers to the Technology sector.

Step 8: Generate at least {0} search queries that could be used to find recent financial news on the web
about the industries and sectors identified at step 7. If the TERM OF INTEREST refers to all indsutries, don't include
into the list of search terms any specific industries.

Step 9: Identify other terms that are closely related to the TERM of INTEREST, including competitors.
For example VOO is closely related to SPY because they track the same index. 
For example the US economy is closely related to SPY.
For example Nio is a competitor for Tesla.

Step 10: Generate at least {0} search queries that could be used to find recent financial news on the web
about the other terms identified at step 9. 

In any of the above search terms please replace any year with 'latest'.
If the TERM OF INTEREST does not refer to finance or economics, please leave the whole output empty.

TERM OF INTEREST: {1}
'''


SEARCH_TERM_GENERATION_RESPONSE_FORMAT = """
Use the following JSON schema and make sure that the output can be parsed into JSON format.
Don't include into the output anything else than the JSON schema.

Return: 
{
    "query_meaning": str,
    "list_search_terms": list[str],
    "tracked_index": str,
    "list_search_terms_tracked_index": list[str],
    "country_or_region": str,
    "list_search_terms_country_or_region": list[str],
    "industries_and_sectors": str,
    "list_search_terms_industries_and_sectors": list[str],
    "related_terms": str,
    "list_search_terms_related_terms": list[str]
}
"""


NUMBER_SEARCH_TERMS_EACH_STEP = 5


def _aggregate_search_terms(query: str, llm_response_content: dict[str, list[str]]) -> list[str]:
    """
    Aggregate search terms from the LLM answer
    
    Args:
        query (str): The initial query
        llm_response_content (dict): The content of the LLM response to the summary generation request
    
    Returns:
        A sorted list of all generated search terms (including the original query)
    """
    
    search_terms = set()
    
    for k in ['list_search_terms', 'list_search_terms_tracked_index', 'list_search_terms_country_or_region', 
              'list_search_terms_industries_and_sectors', 'list_search_terms_related_terms']:
        search_terms.update(llm_response_content[k])

    if query not in search_terms:
        search_terms.add(query)

    return sorted(list(search_terms))
    
            
def generate_search_terms(query: str, sink: ProgressSink) -> GenerateRecentNews:
    """
    Generate recent news based on the input query.
    
    Args:
        query (str): The initial news generation request
        sink (ProgressSink): A message sink to which progress messages are sent
    
    Returns:
        GenerateRecentNews: A new object with query meaning and generated search terms based on the query
    """

    timestamp_start = get_and_log_current_time(message=f'The generation of the search terms for {query} started at', sink=sink)   
    
    LLM_response = llm_client.ask_LLM(
        prompt=SEARCH_TERM_GENERATION_PROMPT_TEMPLATE.format(NUMBER_SEARCH_TERMS_EACH_STEP, query) + SEARCH_TERM_GENERATION_RESPONSE_FORMAT, 
        cache_prefix=(query, "search terms")
    )
    
    if LLM_response['status_code'] != 200:
        raise Exception(f'An exception occurred during the LLM call for {(query, "search terms")}')
        
    response_content = LLM_response['response_content']
    
    query_meaning = response_content["query_meaning"]
    sink.send(message=f"The meaning of the query is: {query_meaning}")
    log.info(msg=f"The meaning of the query is: {query_meaning}\n")

    search_terms = _aggregate_search_terms(query=query, llm_response_content=response_content)
    
    sink.send(message=f"Generated {len(search_terms)} search terms")
    log.info(msg=f"Generated {len(search_terms)} search terms\n")

    timestamp_end = get_and_log_current_time(message=f'The generation of the search terms for {query} finished at', sink=sink)

    log_processing_duration(timestamp_start=timestamp_start, timestamp_end=timestamp_end, message=f'The generation of the search terms for {query}', sink=sink)
    
    return GenerateRecentNews(
        query=query,
        query_meaning=query_meaning,
        search_terms=search_terms
    )
