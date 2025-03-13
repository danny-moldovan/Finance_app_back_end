import duckduckgo_client
from utils import *
import time
from cache import cache

NEWS_RESULT_COUNT = 10


@cache.memoize(timeout = 60 * 60) #1 hour in seconds
def perform_search_one_term(s):
    try:
        search_results = duckduckgo_client.duckduckgo_client.news(
            keywords = s, 
            region = "us-en", #or "wt-wt" ?
            #safesearch = "off", 
            timelimit = "d", #results from today only
            max_results = NEWS_RESULT_COUNT
        )
    
        return [n['url'] for n in search_results]

    except Exception as e:
        log.info('Error: {}'.format(e))
        log.info('')
        return []

def perform_search_per_batch(i, batch, return_dict):
    count_results_per_batch = 0

    '''
    for s in batch:
        print('Searching {}'.format(s))
        news_results = news_search_client.news.search(
                query = s, 
                market = "en-us", 
                freshness = "Day",
                sort_by = "Date",
                count = NEWS_RESULT_COUNT
                )
        return_dict[s] = [n.url for n in news_results.value]
        count_results_per_batch += len([n.url for n in news_results.value])
    '''

    for s in batch:
        
        '''
        news_results = DDGS().news(keywords = s, 
                          region = "us-en", #or "wt-wt" ?
                          #safesearch = "off", 
                          timelimit = "d", #results from today only
                          max_results = NEWS_RESULT_COUNT)        

        return_dict[s] = [n['url'] for n in news_results]
        count_results_per_batch += len([n['url'] for n in news_results])
        '''

        return_dict[s] = perform_search_one_term(s)
        count_results_per_batch += len(return_dict[s])
        
        #Available fields: date, title, body, url, image, source

    log.info('For batch number {} (of length {}) found {} results'.format(i + 1, len(batch), count_results_per_batch))
    log.info('')


def search_web(all_search_terms, batch_size = 1, max_time_per_batch = 10):
    time_start = time.time()
    
    yield log_message('Searching the web')
    log.info('Searching the web')
    log.info('')

    try:
        if len(all_search_terms) == 0:
            raise Error('No search terms to be searched')
            
        batches = create_batches(all_search_terms, batch_size) #or: len(all_search_terms) // 3
        yield log_message('Created {} batches of search requests'.format(len(batches)))
        log.info('Created {} batches of search requests \n'.format(len(batches)))
        log.info('')
        
        search_results = run_multiple_with_limited_time(perform_search_per_batch, batches, max_time_per_batch)
    
        agg_search_results = set()
    
        for k in search_results.keys():
            if search_results[k] is not None:
                for u in search_results[k]:
                    agg_search_results.add(u)
    
        agg_search_results = list(agg_search_results)
        yield log_message('Found {} distinct web results'.format(len(agg_search_results)))
        log.info('Found {} distinct web results\n'.format(len(agg_search_results)))
        log.info('')
        
        for s in agg_search_results:
            yield value_message(s)

    except Exception as e:
        log.info('Error: {}'.format(e))
        log.info('')
        yield log_message('Error: {}'.format(e))

    time_end = time.time()
    log.info('Elapsed: {} seconds'.format(int((time_end - time_start) * 100) / 100))
    log.info('')
        