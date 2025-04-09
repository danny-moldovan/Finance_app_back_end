import time
from websearch import *
from webpage_retrieval import *
from duckduckgo_client import *
from ratelimit import limits, sleep_and_retry
from multiprocessing import Process, Manager, Lock


test_search_term = 'US stocks'
test_url = 'https://www.forbes.com/advisor/money-transfer/currency-converter/inr-usd/'
#'http://google.com' #'https://www.forbes.com/advisor/money-transfer/currency-converter/inr-usd/'


def perform_search_one_term2(s):
    try:
        search_results = duckduckgo_client.news(
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
        
        
@sleep_and_retry
@limits(calls = 20, period = 1)  # 20 requests per second
def crawl_url_using_crawlbase_test1(url):
    return "Success", ""


def crawl_url_using_crawlbase_test2(url):
    return "Success", ""
    

def test_rate_limiter(f, param, n):
    start_time = time.time()

    for _ in range(n):
        result = f(param)
        if isinstance(result, tuple):
            crawling_success, text = result
            print('{}: {}'.format(time.time(), crawling_success))
        else:
            print('{}: {}'.format(time.time(), len(result)))

    end_time = time.time()
    elapsed_time = end_time - start_time

    print(f"Total time taken: {elapsed_time:.2f} seconds")
    print(f"Expected time (min): {n / 20:.2f} seconds")


def test_rate_limiter_multiprocessing(f, param, n):
    start_time = time.time()
    
    def wrapper_function(i, param, return_dict):
        result = f(param)
        return_dict[i] = '{}: {}'.format(time.time(), len(result))
        print(return_dict[i])
    
    results = run_multiple_with_limited_time(wrapper_function, [param for _ in range(n)], max_time = None)

    end_time = time.time()
    elapsed_time = end_time - start_time

    print(f"Total time taken: {elapsed_time:.2f} seconds")
    print(f"Expected time (min): {n / 20:.2f} seconds")

    n_successful = len([k for k in results.keys() if int(results[k].split(':')[1].strip()) > 0])
    print('Number of successful requests: {}'.format(n_successful))
    

class RateLimiter:
    def __init__(self, max_requests_per_sec):
        self.max_requests = max_requests_per_sec
        self.request_count = Manager().Value("i", 0)
        self.lock = Lock()

    def reset_count(self):
        """Runs in a background process to reset the request count every second."""
        while True:
            time.sleep(1)  # Reset every second
            with self.lock:
                self.request_count.value = 0

    def acquire(self):
        """Blocks if the request limit is reached and waits until allowed."""
        while True:
            with self.lock:
                if self.request_count.value < self.max_requests:
                    self.request_count.value += 1
                    return  # Proceed with the request
            time.sleep(0.1)  # Check again in 100ms
            

def test_rate_limiter_across_processes(f, param, n):
    rate_limiter = RateLimiter(max_requests_per_sec = 5)

    # Start background process to reset request count
    reset_process = Process(target = rate_limiter.reset_count, daemon = True)
    reset_process.start()

    start_time = time.time()
    
    def wrapper_function(i, param, return_dict, rate_limiter = rate_limiter):
        rate_limiter.acquire()
        result = f(param)
        return_dict[i] = '{}: {}'.format(time.time(), len(result))
        print(return_dict[i])
    
    results = run_multiple_with_limited_time(wrapper_function, [param for _ in range(n)], max_time = None)

    end_time = time.time()
    elapsed_time = end_time - start_time

    print(f"Total time taken: {elapsed_time:.2f} seconds")
    print(f"Expected time (min): {n / 20:.2f} seconds")

    n_successful = len([k for k in results.keys() if int(results[k].split(':')[1].strip()) > 0])
    print('Number of successful requests: {}'.format(n_successful))
  
    
if __name__ == "__main__": 
    #test_rate_limiter(crawl_url_using_crawlbase, test_url, 50)
    #test_rate_limiter(crawl_url_using_crawlbase1, test_url, 50)
    #test_rate_limiter(crawl_url_using_crawlbase2, test_url, 50)

    #test_rate_limiter(perform_search_one_term, test_search_term, 50) #83s       
    #test_rate_limiter(perform_search_one_term2, test_search_term, 50)  #83s
    
    #test_rate_limiter_multiprocessing(perform_search_one_term, test_search_term, 50) #1.16s, only is able to process 37
    #test_rate_limiter_multiprocessing(perform_search_one_term2, test_search_term, 50) #1.16s, only is able to process 37

    test_rate_limiter_across_processes(perform_search_one_term, test_search_term, 500) #25s for 50 requests, 50s for 100 requests
        #For 500 requests: 
        #Retry after 0.1s, max 2 req./s: 250s, 500 OK
        #Retry after 0.1s, max 3 req./s: 167s, 499 OK
        #Retry after 0.1s, max 4 req./s: 126s, 454 OK
        #Retry after 0.1s, max 5 req./s: 100s, 371 OK
        #Retry after 0.05s, max 5 req./s: 101s, 380 OK
        #Retry after 0.01s, max 5 req./s: 103s, 384 OK





