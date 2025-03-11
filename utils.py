from multiprocessing import Process, Manager
import os
import json
import logging

log = logging.getLogger('logger')
log.setLevel(logging.DEBUG)
formatter = logging.Formatter('%(message)s')

file_handler = logging.FileHandler('logs_back_end.log', mode = 'w', encoding = 'utf-8')
file_handler.setLevel(logging.DEBUG)
file_handler.setFormatter(formatter)
log.addHandler(file_handler)

screen_handler = logging.StreamHandler()
screen_handler.setLevel(logging.DEBUG)
screen_handler.setFormatter(formatter)
log.addHandler(screen_handler)


GEMINI_REASONING_MODEL_NAME = "gemini-2.0-flash-thinking-exp"

def run_multiple_with_limited_time(func, args, max_time, **kwargs):
    manager = Manager()
    return_dict = manager.dict()

    n = len(args)
    jobs = []

    for i in range(n):
        p = Process(target = func, args = (i, args[i], return_dict,), kwargs = kwargs)
        jobs.append(p)
        p.start()

    #print(len(jobs), 'jobs started')

    for i in range(len(jobs)):
        p = jobs[i]
        p.join(max_time)
        if p.is_alive():
            p.terminate()
            #return_dict[args[i]] = None #or []?

    return return_dict

def create_batches(a, batch_size):
    return [a[i: i + batch_size] for i in range(0, len(a), batch_size)]

def search_cache(cache_path, key):
    if not os.path.isfile(cache_path):
        return None

    with open(cache_path, 'rb') as f:
        cached_data = pickle.load(f)

    return cached_data.get(key, None)

def update_cache(cache_path, additional_data):
    if not os.path.isfile(cache_path):
        updated_dict = additional_data
    else:
        with open(cache_path, 'rb') as f:
            cache = pickle.load(f)
        
        for k in additional_data.keys():
                cache[k]= additional_data[k]
            
        with open(cache_path, 'wb') as f:
            pickle.dump(cache, f)

    return cache

def parse_message_sent(m): 
    m_parsed = json.loads(m[:-1])
        
    return m_parsed["return_type"], m_parsed["return_value"]

def log_message(m):
    return json.dumps({"return_type": "log", "return_value": m}) + "\n"

def value_message(m):
    return json.dumps({"return_type": "value", "return_value": m}) + "\n"
