import time
import json
from utils import *
import gemini_client
from cache import cache

AGGREGATION_PROMPT_TEMPLATE = '''For each of the below ARTICLES please perform the following 2 steps:
Step 1: Identify whether the ARTICLE IMPACT ON THE TERM OF INTEREST is grounded by the ARTICLE TEXT
Step 2: Identify whether the ARTICLE TEXT has a positive or a negative impact on the TERM of INTEREST. 
Exclude the ARTICLES that have a neutral impact on the TERM OF INTEREST.
Afterwards please perform the following step:
Step 3: Build a list of the most important at most 5 recent news about the TERM OF INTEREST, which have been 
aggregated from the ARTICLES at step 2.
Order the news in decreasing order of their impact on the TERM OF INTEREST.
Make sure that each news has a different topic and that there are no duplicates among the news.
Aggregte news having the same topic. Forexample if two news both refer to the US monetary policy or its consequences,
please aggregate them into one news.
If there are less than 5 distinct news then please provide less than 5 of them.
If the list of ARTICLES at step 2 don't contain any impact on the TERM of INTEREST, please leave the output empty.
For each news please include the most relevant URL from the ones at step 2 and an explanation of the impact of the news on the TERM OF INTEREST.

TERM OF INTEREST: {}

'''

agg_response_format_prompt = \
        """

Use the following JSON schema and make sure that the output can be parsed into JSON format.
Don't include into the output anything else than the JSON schema.
The field "impact_of_news_on_term_of_interest" should contain an explanation of the impact of the news on the TERM OF INTEREST.
The field "impact_type_of_news" should be derived from the field "impact_on_term_of_interest" and it should contain one of the values
"positive" or "negative".

Return: 
{
  "items": [
    {
      "news": "string",
      "most_relevant_article_url": "string",
      "impact_of_news_on_term_of_interest": "string",
      "impact_type_of_news": "string"
    }
  ]
}

        """

@cache.memoize(timeout = 60 * 60) #1 hour in seconds
def ask_llm_to_generate_aggregated_output(prompt):
    response = gemini_client.gemini_client.models.generate_content(
        model = GEMINI_REASONING_MODEL_NAME,
        contents = prompt
    )

    return response.candidates[0].content.parts[0].text.replace('`', '')
    
    
def generate_aggregated_output(term_of_interest_meaning, summary_completions, extracted_content_from_search_results):
    time_start = time.time()

    log.info('Processing aggregation of the LLM outputs and generating final output')
    log.info('')
    yield log_message('Processing aggregation of the LLM outputs and generating final output')

    try:
        agg_prompt = AGGREGATION_PROMPT_TEMPLATE.format(term_of_interest_meaning)
        
        for completion in summary_completions:
            for item in completion:
                url = item['article_url']
                if url not in extracted_content_from_search_results.keys():
                    log.info('{} not parsed'.format(url))
                    log.info('')
                else:
                    agg_prompt += 'Article ' + item['article_number'] + \
                        '\nArticle URL: ' + url + \
                        '\nArticle text: ' + extracted_content_from_search_results[url] + \
                        '\nArticle impact on the term of interest: ' + item['impact_on_term_of_interest'] + \
                        '\nArticle impact type: ' + item['impact_type'] + '\n\n'
    
        #print('Aggregated prompt: ', agg_prompt + agg_response_format_prompt)
        log.info('Aggregated prompt length: {}'.format(len(agg_prompt + agg_response_format_prompt)))
        log.info('')
        #print(agg_prompt + agg_response_format_prompt)
        #print()
    
        r = ask_llm_to_generate_aggregated_output(agg_prompt + agg_response_format_prompt)
        n = len(r)
        final_output = json.loads(r[5: n - 1])['items']
        #print(final_output)
        #print()
        
        for item in final_output:
            log.info('News: {}'.format(item['news']))
            log.info('Most relevant URL: {}'.format(item['most_relevant_article_url']))
            log.info('Impact on the term of interest: {}'.format(item['impact_of_news_on_term_of_interest']))
            log.info('Impact type: {}'.format(item['impact_type_of_news']))
            log.info('')
    
            yield value_message('News: {}\n'.format(item['news']))
            yield value_message('Most relevant URL: {}\n'.format(item['most_relevant_article_url']))
            yield value_message('Impact on the term of interest: {}\n'.format(item['impact_of_news_on_term_of_interest']))
            yield value_message('Impact type: {}\n'.format(item['impact_type_of_news']))

    except Exception as e:
        log.info('Error: {}'.format(e))
        log.info('')
        yield log_message('Error: {}'.format(e))
        
    time_end = time.time()
    log.info('Elapsed: {} seconds'.format(int((time_end - time_start) * 100) / 100))
    log.info('')
    