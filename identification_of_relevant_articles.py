from typing import Any, Callable
from utils import log, get_and_log_current_time, log_processing_duration, run_multiple_with_limited_time
from llm_client import llm_client
from generate_recent_news import GenerateRecentNews, Article, ImpactType
from progress_sink import ProgressSink


NUMBER_OF_COMPLETIONS = 3
MAX_TIME_IDENTIFICATION_OF_RELEVANT_ARTICLES = None


IDENTIFICATION_OF_RELEVANT_ARTICLES_PROMPT_TEMPLATE = \
"""Please extract the most important news about the TERMS OF INTEREST, based on the below 
ARTICLE URLs and the ARTICLE TEXTs.
Please provide the answer as 10 items at most, each one consisting about important news about the TERM OF INTEREST and its impact 
on the outlook of the TERM OF INTEREST (specifically on its price if the TERM OF INTEREST is a financial instrument) as well as 
the most relevant ARTICLE URL which contains this news.
Please order the items in decreasing order of the magnitude of the impact on the ARTICLEs on the TERM OF INTEREST.

TERM OF INTEREST: {0}
"""


IDENTIFICATION_OF_RELEVANT_ARTICLES_RESPONSE_FORMAT = \
"""

Use the following JSON schema and make sure that the output can be parsed into JSON format.
Don't include into the output anything else than the JSON schema.
The field "article_number" should only contain an integer number, no other characters.
The field "impact_on_term_of_interest" should contain an explanation of the impact of the article on the TERM OF INTEREST.
The field "impact_type" should be derived from the field "impact_on_term_of_interest" and it should contain one of the values
"positive", "negative" or "neutral".
Make sure that the impact on the term of interest and the impact type are all written in English.

Return: 
{
  "items": [
    {
      "article_number": "string",
      "article_url": "string",
      "impact_on_term_of_interest": "string",
      "impact_type": "string"
    }
  ]
}

"""


def _create_llm_wrapper(LLM_request_function: Callable, query: str) -> Callable[[tuple[int, str]], dict[str, Any]]:
    """
    Creates a wrapper function for LLM requests
    
    Args:
        LLM_request_function (Callable): The LLM request function to wrap
        query (str): The query to include into cache prefix
    
    Returns:
        Callable: A function that for an argument (ordered_prompt, containing the index and the prompt) and a list of results (results)
        appends the LLM response for the ordered_prompt to the list of results
    """
    return lambda ordered_prompt, results: results.append(LLM_request_function(
        prompt=ordered_prompt[1],
        cache_prefix=(query, f"relevant articles {ordered_prompt[0] + 1}")
    ))


def _build_identification_of_relevant_articles_prompt(recent_news: GenerateRecentNews) -> str:
    """
    Builds the prompt that will be sent to the LLM for identifying relevant articles.
    The prompt includes the query meaning and all parsed article URLs with their content.
    
    Args:
        recent_news (GenerateRecentNews): The recent news generation request containing parsed URLs and their content
    
    Returns:
        str: The complete prompt that will be sent to the LLM, including the template, articles, and response format
    """

    # Start with the template and query meaning
    prompt_parts = [IDENTIFICATION_OF_RELEVANT_ARTICLES_PROMPT_TEMPLATE.format(recent_news.query_meaning)]
    
    # Add articles in sorted order
    for idx, (url, content) in enumerate(sorted(recent_news.parsed_urls.items()), 1):
        prompt_parts.append(f'ARTICLE {idx}: \n URL: {url} \n TEXT: {content} \n \n')
    
    # Add response format
    prompt_parts.append(IDENTIFICATION_OF_RELEVANT_ARTICLES_RESPONSE_FORMAT)
    
    prompt = ''.join(prompt_parts)
    
    log.info(f'The prompt for the identification of relevant articles for {recent_news.query} contains {len(prompt)} characters\n')
    
    return prompt


def _parse_LLM_responses(
    query: str,
    LLM_responses: list[dict[str, Any]],
    sink: ProgressSink
) -> list[list[Article]]:
    """
    Extracts and processes the lists of relevant articles identified from the LLM responses.
    Filters out articles with neutral impact and converts the response into Article objects.
    
    Args:
        query (str): The initial query used for article identification
        LLM_responses (list[dict[str, Any]]): A list of LLM response dictionaries containing article information
        sink (ProgressSink): A sink for logging progress and results
    
    Returns:
        list[list[Article]]: A list of lists containing Article objects, one list per LLM response
    """

    relevant_articles = []
    valid_impact_types = {'positive', 'negative'}

    for idx, response in enumerate(LLM_responses, 1):
        try:
            if response.get('status_code') != 200:
                log.info(f'The LLM completion {idx} had an issue: {response.get("status_code")}\n')
                relevant_articles.append([])
                continue
                
            items = response.get('response_content', {}).get('items', [])
            if not items:
                log.info(f'The LLM completion {idx} returned no items\n')
                relevant_articles.append([])
                continue
                
            # Process valid items with positive or negative impact
            list_articles = [
                Article(
                    article_number=''.join(filter(str.isdigit, str(item.get('article_number', '')))),
                    article_url=item.get('article_url', ''),
                    impact_summary_on_query=item.get('impact_on_term_of_interest', ''),
                    impact_type_on_query=ImpactType(item.get('impact_type', ''))
                ) for item in items 
                if item.get('impact_type') in valid_impact_types
            ]
            relevant_articles.append(list_articles)
            
        except Exception as e:
            log.info(f'Error processing LLM completion {idx}: {str(e)}\n')
            relevant_articles.append([])

    article_counts = [len(x) for x in relevant_articles]
    result_message = f'The counts of relevant articles identified for {query} are: {article_counts}'
    sink.send(result_message)
    log.info(f'{result_message}\n')

    return relevant_articles


def identify_relevant_articles(
    recent_news: GenerateRecentNews,
    sink: ProgressSink,
    number_of_completions: int = NUMBER_OF_COMPLETIONS
) -> GenerateRecentNews:
    """
    Identifies articles relevant to a query by analyzing the parsed article content.
    
    Args:
        recent_news (GenerateRecentNews): The news generation request containing parsed URLs and their content
        sink (ProgressSink): A sink for logging progress and results
        number_of_completions (int, optional): Number of LLM completions to generate. Defaults to NUMBER_OF_COMPLETIONS
    
    Returns:
        GenerateRecentNews: A new object containing the original query plus identified relevant articles
    
    Raises:
        Exception: If no URLs have been parsed or if an error occurs during processing
    """

    # Validate input
    if not recent_news.parsed_urls:
        raise ValueError("No URLs have been parsed")
    
    # Start timing
    timestamp_start = get_and_log_current_time(
        message=f'The identification of relevant articles for {recent_news.query} started at',
        sink=sink
    )
    
    try:
        # Build the prompt
        identification_of_relevant_articles_prompt = _build_identification_of_relevant_articles_prompt(
            recent_news=recent_news
        )
        
        # Create the wrapper function for LLM requests
        llm_wrapper = _create_llm_wrapper(llm_client.ask_LLM, recent_news.query)
        
        # Prepare arguments for multiple LLM requests
        llm_args = [(idx, identification_of_relevant_articles_prompt) 
                   for idx in range(number_of_completions)]
        
        # Run multiple LLM requests with timeout
        LLM_responses = list(run_multiple_with_limited_time(
            func=llm_wrapper,
            args=llm_args,
            max_time=MAX_TIME_IDENTIFICATION_OF_RELEVANT_ARTICLES
        ))
        
        # Parse the LLM responses
        relevant_articles = _parse_LLM_responses(
            query=recent_news.query,
            LLM_responses=LLM_responses,
            sink=sink
        )
        
        # End timing and log duration
        timestamp_end = get_and_log_current_time(
            message=f'The identification of relevant articles for {recent_news.query} finished at',
            sink=sink
        )
        log_processing_duration(
            timestamp_start=timestamp_start,
            timestamp_end=timestamp_end,
            message=f'The identification of relevant articles for {recent_news.query}',
            sink=sink
        )
        
        # Return the updated GenerateRecentNews object
        return GenerateRecentNews(
            query=recent_news.query,
            query_meaning=recent_news.query_meaning,
            search_terms=recent_news.search_terms,
            retrieved_urls=recent_news.retrieved_urls,
            parsed_urls=recent_news.parsed_urls,
            relevant_articles=relevant_articles
        )
        
    except Exception as e:
        # Log the exception and re-raise it
        log.info(f'An exception occurred during the identification of relevant articles for {recent_news.query}: {e}\n')
        raise
