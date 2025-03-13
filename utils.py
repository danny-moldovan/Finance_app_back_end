from multiprocessing import Process, Manager
import os
import json
import logging
from google.cloud import storage
import google.auth

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

def authenticate_gcs():
    try:
        credentials, project = google.auth.default()
        print(f"Authenticated with project: {project}")
        return credentials
    except Exception as e:
        print(f"Authentication failed: {e}")
        return None

def download_from_gcs(bucket_name, source_blob_name, destination_file_name):
    """Downloads a file from Google Cloud Storage."""
    try:
        storage_client = storage.Client()
        bucket = storage_client.bucket(bucket_name)
        blob = bucket.blob(source_blob_name)
        blob.download_to_filename(destination_file_name)
        print(f"Downloaded {source_blob_name} from {bucket_name} to {destination_file_name}")
    except Exception as e:
        print(f"Error downloading file: {e}")

def upload_to_gcs(bucket_name, source_file_name, destination_blob_name):
    """Uploads a file to Google Cloud Storage."""
    try:
        storage_client = storage.Client()
        bucket = storage_client.bucket(bucket_name)
        blob = bucket.blob(destination_blob_name)
        blob.upload_from_filename(source_file_name)
        print(f"Uploaded {source_file_name} to gs://{bucket_name}/{destination_blob_name}")
    except Exception as e:
        print(f"Error uploading file: {e}")
        