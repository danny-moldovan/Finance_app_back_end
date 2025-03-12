import time
import datetime
import json
from utils import *
import gemini_client
from cache import cache
import dill
import os

N_COMPLETIONS = 3
MAX_TIME_SUMMARY_GENERATION = 80

identification_of_relevant_articles_requests_filename = '/teamspace/studios/this_studio/back_end/identification_of_relevant_articles.pkl'


SUMMARY_GENERATION_PROMPT_TEMPLATE = '''Please extract the most important news about the TERMS OF INTEREST, based on the below 
ARTICLE URLs and the ARTICLE TEXTs.
Please provide the answer as 10 items at most, each one consisting about important news about the TERM OF INTEREST and its impact 
on the outlook of the TERM OF INTEREST (specifically on its price if the TERM OF INTEREST is a financial instrument) as well as 
the most relevant ARTICLE URL which contains this news.
Please order the items in decreasing order of the magnitude of the impact on the ARTICLEs on the TERM OF INTEREST.

TERM OF INTEREST: {}
'''

summary_generation_response_format_prompt = \
        """
        
        Use the following JSON schema and make sure that the output can be parsed into JSON format.
        Don't include into the output anything else than the JSON schema.
        The field "impact_on_term_of_interest" should contain an explanation of the impact of the article on the TERM OF INTEREST.
        The field "impact_type" should be derived from the field "impact_on_term_of_interest" and it should contain one of the values
        "positive", "negative" or "neutral".

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

@cache.memoize(timeout = 60 * 60) #1 hour in seconds
def ask_llm_to_generate_summary(prompt):
    response = gemini_client.gemini_client.models.generate_content(
        model = GEMINI_REASONING_MODEL_NAME,
        contents = prompt
    )

    return response.candidates[0].content.parts[0].text.replace('`', '')
    

def send_summary_generation_request_to_llm(i, prompt, return_dict):
    r = ask_llm_to_generate_summary(prompt)
    n = len(r)
    parsed_output = json.loads(r[5: n - 1])['items']

    '''
    if not os.path.isfile(identification_of_relevant_articles_requests_filename):
        with open(identification_of_relevant_articles_requests_filename, 'wb') as f:
            dill.dump({}, f)
        serialized_requests = {}
        print('Initialized the file')
    else:
        with open(identification_of_relevant_articles_requests_filename, 'rb') as f:
            serialized_requests = dill.load(f)
        print('Loaded the file')

    found_exact_match = False
    
    for k in serialized_requests.keys():
        if serialized_requests[k]['prompt'] == prompt:
            print('Found exact match with the prompt sent at {}'.format(k))
            found_exact_match = True

    if not found_exact_match:
        print('Did not find any exact match with previously sent prompts')

    serialized_requests[str(datetime.datetime.now())] = {'prompt': prompt, 'answer': parsed_output}

    with open(identification_of_relevant_articles_requests_filename, 'wb') as f:
        dill.dump(serialized_requests, f)
    '''
    
    return_dict[i] = parsed_output
    

def generate_summary_completions(term_of_interest_meaning, extracted_content_from_search_results, N_completions = N_COMPLETIONS):
    time_start = time.time()
    
    log.info('Asking an LLM to identify relevant articles and generate summaries')
    log.info('')
    yield log_message('Asking an LLM to identify relevant articles and generate summaries')

    try:    
        summary_generation_prompt = SUMMARY_GENERATION_PROMPT_TEMPLATE.format(term_of_interest_meaning)
        
        article_count = 1
    
        extracted_content_from_search_results_sorted_keys = sorted(list(extracted_content_from_search_results.keys()))
        
        for url in extracted_content_from_search_results_sorted_keys:
            if extracted_content_from_search_results[url] is not None:
                summary_generation_prompt += 'ARTICLE {}: \n URL: {} \n TEXT: {} \n \n'.format(article_count, 
                                                                            url,
                                                                            extracted_content_from_search_results[url]
                                                                           )
                article_count += 1
    
                
        log.info('Prompt length: {}'.format(len(summary_generation_prompt + summary_generation_response_format_prompt)))
        log.info('')
    
        completions = run_multiple_with_limited_time(send_summary_generation_request_to_llm,
                                                     [summary_generation_prompt + summary_generation_response_format_prompt] * N_completions, 
                                                     MAX_TIME_SUMMARY_GENERATION
                                                    )
    
        for idx in completions.keys():
            log.info('LLM output {} returned {} items'.format(idx + 1, len(completions[idx])))
            log.info('')
            yield log_message('LLM output {} returned {} items'.format(idx + 1, len(completions[idx])))
    
            '''
            for item in completions[idx]:
                print('Article:', item['article_number'])
                print('URL:', item['article_url'])
                print('Impact on the term of interest:', item['impact_on_term_of_interest'])
                print('Impact type:', item['impact_type'])
                print()
            
            print()
            '''
    
            '''
            for item in completions[idx]:
                yield idx, 'Article', item['article_number']
                yield idx, 'URL', item['article_url']
                yield idx, 'Impact on the term of interest', item['impact_on_term_of_interest']
                yield idx, 'Impact type', item['impact_type']
            '''
    
            yield value_message(completions[idx])

    except Exception as e:
        log.info('Error: {}'.format(e))
        log.info('')
        yield log_message('Error: {}'.format(e))

    time_end = time.time()
    log.info('Elapsed: {} seconds'.format(int((time_end - time_start) * 100) / 100))
    log.info('')
