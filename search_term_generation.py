import time
from utils import *
import gemini_client
import json
from cache import cache

#search_terms_cache_filename = 'search_terms_cache.pkl'


QUERY_UNDERSTANDING_PROMPT_TEMPLATE = '''Please perform the following steps:
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

response_format_prompt = """
        
        Use the following JSON schema and make sure that the output can be parsed into JSON format.
        Don't include into the output anything else than the JSON schema.

        Return: 
        {
            term_meaning: str
            list_search_terms: list[str]
            tracked_index: str
            list_search_terms_tracked_index: list[str]
            country_or_region: str
            list_search_terms_country_or_region: list[str]
            industries_and_sectors: str
            list_search_terms_industries_and_sectors: list[str]
            related_terms: str
            list_search_terms_related_terms: list[str]
            list[str]
        }
        """

@cache.memoize(timeout = 60 * 60) #1 hour in seconds
def ask_llm_to_generate_search_terms(query, n_search_terms_each_step = 5):
    response = gemini_client.gemini_client.models.generate_content(
        model = GEMINI_REASONING_MODEL_NAME,
        contents = QUERY_UNDERSTANDING_PROMPT_TEMPLATE.format(n_search_terms_each_step, query) + response_format_prompt
    )

    return response.candidates[0].content.parts[0].text.replace('`', '')


def generate_search_terms(query, n_search_terms_each_step = 5):
    time_start = time.time()

    yield log_message('Generating search terms')
    log.info('Generating search terms')
    log.info('')

    try:
        if query is None or len(query) == 0:
            raise Error('Invalid query')
            
        r = ask_llm_to_generate_search_terms(query, n_search_terms_each_step)
        n = len(r)
        query_understand_results = json.loads(r[5: n - 1])
    
        all_search_terms = set()
        for k in ['list_search_terms', 'list_search_terms_tracked_index', 'list_search_terms_country_or_region', 
            'list_search_terms_industries_and_sectors', 'list_search_terms_related_terms']:
            for s in query_understand_results[k]:
                all_search_terms.add(s)
    
        all_search_terms = list(all_search_terms)
    
        if query not in all_search_terms:
            all_search_terms.append(query)
    
        query_meaning = query_understand_results['term_meaning']
        log.info('Term meaning: {}'.format(query_meaning))
        log.info('')
    
        yield log_message('Generated {} search terms'.format(len(all_search_terms)))
        log.info('Generated {} search terms'.format(len(all_search_terms)))
        #print(all_search_terms)
        log.info('')
        
        yield value_message(query_meaning)
    
        for s in all_search_terms:
            yield value_message(s)

    except Exception as e:
        log.info('Error: {}'.format(e))
        log.info('')
        yield log_message('Error: {}'.format(e))

    time_end = time.time()
    log.info('Elapsed: {} seconds'.format(int((time_end - time_start) * 100) / 100))
    log.info('')
        