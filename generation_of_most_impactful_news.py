import json
from generate_recent_news import GenerateRecentNews, ImpactType, News, Article
from llm_client import llm_client
from progress_sink import ProgressSink
from utils import get_and_log_current_time, log, log_processing_duration


GENERATION_OF_MOST_IMPACTFUL_NEWS_PROMPT_TEMPLATE = \
"""For each of the below ARTICLES please perform the following 2 steps:
Step 1: Identify whether the ARTICLE IMPACT ON THE TERM OF INTEREST is grounded by the ARTICLE TEXT
Step 2: Identify whether the ARTICLE TEXT has a positive or a negative impact on the TERM of INTEREST. 
Exclude the ARTICLES that have a neutral impact on the TERM OF INTEREST.
Afterwards please perform the following step:
Step 3: Build a list of the most important at most 5 recent news about the TERM OF INTEREST, which have been 
aggregated from the ARTICLES at step 2.
Order the news in decreasing order of their impact on the TERM OF INTEREST.
Make sure that each news has a different topic and that there are no duplicates among the news.
Aggregte news having the same topic. For example if two news both refer to the US monetary policy or its consequences,
please aggregate them into one news.
If there are less than 5 distinct news then please provide less than 5 of them.
If the list of ARTICLES at step 2 don't contain any impact on the TERM of INTEREST, please leave the output empty.
For each news please include the most relevant URL from the ones at step 2 and an explanation of the impact of the news on the TERM OF INTEREST.

TERM OF INTEREST: {}

"""


GENERATION_OF_MOST_IMPACTFUL_NEWS_RESPONSE_FORMAT = \
"""

Use the following JSON schema and make sure that the output can be parsed into JSON format.
Don't include into the output anything else than the JSON schema.
The field "impact_of_news_on_term_of_interest" should contain an explanation of the impact of the news on the TERM OF INTEREST.
The field "impact_type_of_news" should be derived from the field "impact_on_term_of_interest" and it should contain one of the values
"positive" or "negative".
Make sure that the news, the impact of the news on the term of interest and the impact types are all written in English.

Return: 
{
  "items": [
    {
      "news": "string",
      "most_relevant_url": "string",
      "impact_of_news_on_term_of_interest": "string",
      "impact_type_of_news": "string"
    }
  ]
}

"""


def _build_generation_of_most_impactful_news_prompt(recent_news: GenerateRecentNews) -> str:
    """
    Builds the prompt that will be sent to the LLM for generating the most impactful news.
    
    Args:
        recent_news (GenerateRecentNews): The recent news generation request containing relevant articles
    
    Returns:
        str: The formatted prompt string that will be sent to the LLM
    """

    # Start with the base template
    prompt_parts = [GENERATION_OF_MOST_IMPACTFUL_NEWS_PROMPT_TEMPLATE.format(recent_news.query_meaning)]

    # Sort relevant articles by converting to strings, sorting, and converting back
    relevant_articles_cast_to_strings = [json.dumps([str(article) for article in list_articles]) for list_articles in recent_news.relevant_articles]
    relevant_articles_cast_to_strings.sort()
    relevant_articles_sorted = [[Article.from_string(article_str) for article_str in json.loads(article_list)] for article_list in relevant_articles_cast_to_strings]

    for list_articles in relevant_articles_sorted:
        for article in list_articles:
            prompt_parts.extend([
                f'Article {article.article_number}',
                f'Article URL: {article.article_url}',
                f'Article text: {recent_news.parsed_urls.get(article.article_url, "")}',
                f'Article impact on the term of interest: {article.impact_summary_on_query}',
                f'Article impact type: {article.impact_type_on_query}\n'
            ])

    # Add the response format
    prompt_parts.append(GENERATION_OF_MOST_IMPACTFUL_NEWS_RESPONSE_FORMAT)

    # Join all parts with newlines
    prompt = '\n'.join(prompt_parts)

    # Log the prompt size
    log.info(msg=f'The prompt for the generation of the most impactful news for {recent_news.query} contains {len(prompt)} characters\n')

    return prompt


def _parse_LLM_response(LLM_response: dict) -> list[News]:
    """
    Parses the LLM response into a list of News objects.
    
    Args:
        LLM_response (dict): The response from the LLM containing news items
    
    Returns:
        list[News]: A list of News objects parsed from the LLM response
    """
    
    if not LLM_response or not LLM_response.get('response_content'):
        return []
        
    response_content = LLM_response['response_content']
    news_items = response_content.get('items', [])
    
    parsed_news = []
    for idx, news_item in enumerate(news_items, 1):
        try:
            if not all(key in news_item for key in ['news', 'most_relevant_url', 'impact_of_news_on_term_of_interest', 'impact_type_of_news']):
                log.info(msg=f'News item {idx} missing required fields, skipping\n')
                continue
            
            # Validate impact type before creating News object
            impact_type = news_item['impact_type_of_news'].lower()
            if impact_type not in ['positive', 'negative']:
                log.info(msg=f'News item {idx} has invalid impact type: {impact_type}, skipping\n')
                continue
                
            news = News(
                news_summary=news_item['news'],
                impact_description_on_query=news_item['impact_of_news_on_term_of_interest'],
                impact_type_on_query=ImpactType(impact_type),
                most_relevant_url=news_item['most_relevant_url']
            )
            parsed_news.append(news)
            
        except ValueError as e:
            log.info(msg=f'Invalid impact type in news item {idx}: {str(e)}\n')
            continue
        except Exception as e:
            log.info(msg=f'Error parsing news item {idx}: {str(e)}\n')
            continue
    
    if not parsed_news:
        log.info(msg='No valid news items found in LLM response\n')
    
    return parsed_news


def generate_most_impactful_news(recent_news: GenerateRecentNews, sink: ProgressSink) -> GenerateRecentNews:
    """
    Generates the most impactful news about a query, based on identified relevant articles.
    
    Args:
        recent_news (GenerateRecentNews): The news generation request, having the relevant_articles field populated
        sink (ProgressSink): The progress sink for logging progress and timing information
    
    Returns:
        GenerateRecentNews: A new object with the most impactful news generated
    
    Raises:
        ValueError: If no relevant articles are found
        Exception: If there's an error during LLM processing
    """
    
    try:
        # Validate input
        if not recent_news.relevant_articles:
            raise ValueError("No relevant articles have been identified")
        
        timestamp_start = get_and_log_current_time(
            message=f'The generation of the most impactful news for {recent_news.query} started at',
            sink=sink
        )
        
        # Build and send prompt to LLM
        generation_of_most_impactful_news_prompt = _build_generation_of_most_impactful_news_prompt(
            recent_news=recent_news
        )
        
        LLM_response = llm_client.ask_LLM(
            prompt=generation_of_most_impactful_news_prompt,
            cache_prefix=(recent_news.query, 'most impactful news')
        )
        
        # Validate LLM response
        if LLM_response['status_code'] != 200:
            raise Exception(f'LLM call failed for {recent_news.query} with status code {LLM_response["status_code"]}')
        
        # Parse response and create new object
        most_impactful_news = _parse_LLM_response(LLM_response=LLM_response)
        
        # Log success
        sink.send(f"Generated {len(most_impactful_news)} most impactful news for {recent_news.query}")
        log.info(msg=f"Generated {len(most_impactful_news)} most impactful news for {recent_news.query}\n")
        
        timestamp_end = get_and_log_current_time(
            message=f'The generation of the most impactful news for {recent_news.query} finished at',
            sink=sink
        )
        log_processing_duration(
            timestamp_start=timestamp_start,
            timestamp_end=timestamp_end,
            message=f'The generation of the most impactful news for {recent_news.query}',
            sink=sink
        )
        
        return GenerateRecentNews(
            query=recent_news.query,
            query_meaning=recent_news.query_meaning,
            search_terms=recent_news.search_terms,
            retrieved_urls=recent_news.retrieved_urls,
            parsed_urls=recent_news.parsed_urls,
            relevant_articles=recent_news.relevant_articles,
            most_impactful_news=most_impactful_news
        )

    except ValueError as e:
        log.info(msg=f'Validation error for {recent_news.query}: {str(e)}\n')
        raise
    except Exception as e:
        log.info(msg=f'Error generating most impactful news for {recent_news.query}: {str(e)}\n')
        raise
    