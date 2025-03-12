from bs4 import BeautifulSoup 
import requests
from cache import cache
import time
from utils import *


@cache.memoize(timeout = 60 * 60) #1 hour in seconds
def processWebpage(url):
    try:
        #print('Extracting {}'.format(url))
        response = requests.get(url)
        soup = BeautifulSoup(response.text, 'html.parser') 
        all_tags = soup.find_all() #soup.find_all()
    
        all_text = list()
        for tag in all_tags:
            paragraphs = tag.find_all('p')
            for p in paragraphs:
                p_cleaned = ''.join(i.strip() for i in p.get_text().split('\n'))
                all_text.append(p_cleaned)
    
        all_text_deduplicated = set(all_text)
        #print('Extracted content: {}.'.format(join(all_text_deduplicated)))
    
        return ' '.join(all_text_deduplicated)
    except:
        #print('Exception occured for the URL: {}'.format(url))
        return ''


def extractTextFromURL(i, url, return_dict): 
    return_dict[url] = processWebpage(url)


def extract_content_from_search_results(agg_search_results_list):
    time_start = time.time()
    
    yield log_message('Extracting the content from the websites')
    log.info('Extracting the content from the websites')
    log.info('')

    try:
        extracted_content_from_search_results = run_multiple_with_limited_time(extractTextFromURL, agg_search_results_list, 3)
    
        URLs_could_be_parsed = 0
        
        for k in extracted_content_from_search_results.keys():
            if extracted_content_from_search_results[k] is not None and len(extracted_content_from_search_results[k].strip()) > 0:
                yield value_message({k: extracted_content_from_search_results[k]})
                URLs_could_be_parsed += 1
        
        yield log_message('{} websites could be parsed\n'.format(URLs_could_be_parsed))
        log.info('{} websites could be parsed\n'.format(URLs_could_be_parsed))
        log.info('')

    except Exception as e:
        log.info('Error: {}'.format(e))
        log.info('')
        yield log_message('Error: {}'.format(e))
    
    time_end = time.time()
    log.info('Elapsed: {} seconds\n'.format(int((time_end - time_start) * 100) / 100))
    log.info('')
    