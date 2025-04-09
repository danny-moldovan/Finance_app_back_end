# Standard library imports
import datetime
import logging
import os
import time
from functools import wraps
from multiprocessing import Lock, Manager, Process
from typing import Any, Callable, Optional

# Third-party imports
import google.auth
import requests
from google.cloud import storage

# Local imports
from progress_sink import ProgressSink


LOG_FILENAME = 'logs_back_end.log'
if not os.path.exists(LOG_FILENAME):
    with open(LOG_FILENAME, "w") as f:
        pass 
            
log = logging.getLogger('logger')
log.propagate = True
log.setLevel(logging.DEBUG)
formatter = logging.Formatter('%(message)s')

file_handler = logging.FileHandler(LOG_FILENAME, mode = 'w', encoding = 'utf-8')
file_handler.setLevel(logging.DEBUG)
file_handler.setFormatter(formatter)
log.addHandler(file_handler)

"""
screen_handler = logging.StreamHandler()
screen_handler.setLevel(logging.DEBUG)
screen_handler.setFormatter(formatter)
log.addHandler(screen_handler)
"""

STORAGE_BUCKET_NAME = 'finance-app-back-end-evaluation-logs'
        

def get_and_log_current_time(message: str = '', sink: Optional[ProgressSink] = None) -> datetime.datetime:
    """
    Gets the current time and logs it with an optional message.
    
    Args:
        message (str): Optional message to log with the timestamp
        sink (Optional[ProgressSink]): Optional sink for sending progress messages
    
    Returns:
        datetime.datetime: The current timestamp
    """

    timestamp_now = datetime.datetime.now()
    complete_message = '{}: {}'.format(message, timestamp_now.strftime("%Y-%m-%d %H:%M:%S"))
    log.info(complete_message + '\n')

    if sink is not None:
        sink.send(complete_message)
            
    return timestamp_now


def log_processing_duration(timestamp_start: datetime.datetime, timestamp_end: datetime.datetime, message: str = '', sink: Optional[ProgressSink] = None, unit: str = 'sec') -> None:
    """
    Logs the processing duration between timestamp_start and timestamp_end
    
    Args:
        timestamp_start (datetime.datetime): The start time as a datetime object
        timestamp_end (datetime.datetime): The end time as a datetime object
        message (str): A message to be logged before the duration
        sink (Optional[ProgressSink]): A message sink to which progress messages are sent
        unit (str): The unit to display the duration in ('sec' or 'min'). Defaults to 'sec'.

    Returns:
        None
    """

    duration = (timestamp_end - timestamp_start).total_seconds()
    
    if unit == 'min':
        duration = duration / 60
        unit_str = 'minutes'
    else:
        unit_str = 'seconds'
    
    complete_message = f'{message} took: {duration:.2f} {unit_str}'
    log.info(msg=complete_message + '\n')

    if sink is not None:
        sink.send(complete_message)


def run_multiple_with_limited_time(func: Callable, args: list[Any], max_time: Optional[float] = None) -> list[Any]:
    """
    Runs multiple processes in parallel with a time limit.
    
    Args:
        func (Callable): The function to run in parallel
        args (list[Any]): List of arguments to pass to the function
        max_time (Optional[float]): Maximum time to wait for each process in seconds
    
    Returns:
        list[Any]: List of results from the function calls
    """

    manager = Manager()
    results = manager.list()

    jobs = []

    for arg in args:
        p = Process(target=func, args=(arg, results,))
        jobs.append(p)
        p.start()

    for p in jobs:
        p.join(max_time)
        if p.is_alive():
            p.terminate()

    return results


def convert_to_dictionary(key_value_list: list[dict[str, Any]]) -> dict[str, Any]:
    """
    Converts a list of key:values to a dictionary
    
    Args:
        key_value_list (list[dict[str, Any]]): A list of key:values
    
    Returns:
        dict[str, Any]: A dictionary containing the key:values
    """

    return {k: v for d in key_value_list for k, v in d.items()}


def create_batches(a: list[Any], batch_size: int) -> list[list[Any]]:
    """
    Creates batches of a given size from a list.
    
    Args:
        a (list[Any]): The list to split into batches
        batch_size (int): The size of each batch
    
    Returns:
        list[list[Any]]: List of batches
    """

    return [a[i: i + batch_size] for i in range(0, len(a), batch_size)]


def authenticate_gcs() -> None:
    """
    Authenticates with Google Cloud Storage.
    
    Returns:
        None
    """

    try:
        credentials, project = google.auth.default()
        log.info(f"Authenticated into GCS with project: {project}\n")
    except Exception as e:
        log.info(f"Authentication failed: {e}\n")


def download_from_gcs(source_filename: str, bucket_name: str = STORAGE_BUCKET_NAME, destination_filename: str = '') -> None:
    """
    Downloads a file from Google Cloud Storage.
    
    Args:
        source_filename (str): Name of the file to download
        bucket_name (str): Name of the GCS bucket
        destination_filename (str): Local path to save the file
    
    Returns:
        None
    """

    try:
        storage_client = storage.Client()
        bucket = storage_client.bucket(bucket_name)
        blob = bucket.blob(source_filename)

        if destination_filename == '':
            destination_filename = os.path.join('./data', source_filename)
            
        blob.download_to_filename(destination_filename)
        log.info(f"Downloaded {source_filename} from the Google Storage Bucket {bucket_name} to {destination_filename}\n")
    except Exception as e:
        log.info(f"Error downloading file {source_filename} from the Google Storage Bucket {bucket_name}: {e}\n")


def upload_to_gcs(source_filename: str, bucket_name: str = STORAGE_BUCKET_NAME, destination_filename: str = '') -> None:
    """
    Uploads a file to Google Cloud Storage.
    
    Args:
        source_filename (str): Local path of the file to upload
        bucket_name (str): Name of the GCS bucket
        destination_filename (str): Name to give the file in GCS
    
    Returns:
        None
    """
    
    try:
        storage_client = storage.Client()
        bucket = storage_client.bucket(bucket_name)

        if destination_filename == '':
            destination_filename = source_filename
            
        blob = bucket.blob(destination_filename)
        blob.upload_from_filename(source_filename)
        log.info(f"Uploaded {source_filename} to gs://{bucket_name}/{destination_filename}\n")
    except Exception as e:
        log.info(f"Error uploading file {source_filename} to the Google Storage Bucket {bucket_name}: {e}\n")


class RateLimiter:
    def __init__(self, max_requests_per_sec: int) -> None:
        self.max_requests = max_requests_per_sec
        self.request_count = Manager().Value("i", 0)
        self.lock = Lock()

    def update_max_requests_per_sec(self, max_requests_per_sec: int) -> None:
        self.max_requests = max_requests_per_sec

    def get_max_requests_per_sec(self) -> int:
        return self.max_requests

    def reset_count(self) -> None:
        """Runs in a background process to reset the request count every second."""
        while True:
            time.sleep(2)  # Reset every 2 seconds
            with self.lock:
                self.request_count.value = 0

    def acquire(self) -> None:
        """Blocks if the request limit is reached and waits until allowed."""
        while True:
            with self.lock:
                if self.request_count.value < self.max_requests:
                    self.request_count.value += 1
                    return  # Proceed with the request
            time.sleep(0.1)  # Check again in 0.1 seconds


rate_limiter_search_requests = RateLimiter(max_requests_per_sec=30)
rate_limiter_llm_calls = RateLimiter(max_requests_per_sec=5)


def retry_on_exceeding_rate_limit(max_retries: int = 8, base_delay: float = 3.0, backoff_factor: float = 2.0) -> Callable:
    """
    Retries the decorated function with exponential backoff if a rate limit exceeded or resource exhausted error occurs.

    Args:
        max_retries (int): Maximum number of retries before giving up
        base_delay (float): Initial delay in seconds
        backoff_factor (float): Multiplier for the delay after each retry

    Returns:
        Callable: The decorated function
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            delay = base_delay
            for attempt in range(max_retries):
                try:
                    response = func(*args, **kwargs)
                    if response['status_code'] in (403, 503, 429, 500, 202):
                        log.info(f"{str(args)}: Attempt {attempt + 2}, retrying after {delay} seconds\n")
                        raise requests.exceptions.HTTPError("Rate limit exceeded")
                    return response
                except requests.exceptions.HTTPError as e:
                    if attempt == max_retries - 1:
                        log.info(f"{str(args)}: Maximum number of attempts reached\n")
                        raise
                    time.sleep(delay)
                    delay *= backoff_factor
            return None
        return wrapper
    return decorator


class FileWriter:
    def __init__(self, filename):
        """Initialize the output writer with a file to write to."""
        self.file = open(filename, 'a')  # Open in append mode
        log.info('Outputs will be appended to the file {}\n'.format(filename))
        
    def write(self, message):
        """Write a message to the file."""
        self.file.write(message + '\n')
        self.file.flush()  # Ensure data is written to disk
        
    def close(self):
        """Close the file when done."""
        if not self.file.closed:
            self.file.close()
            
    def __del__(self):
        """Destructor to ensure file is closed if object is garbage collected."""
        self.close()