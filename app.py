# Standard library imports
import json
import threading
from multiprocessing import Queue
from typing import Callable, Generator, Union

# Third-party imports
from flask import Flask, request, Response, stream_with_context
from flask_cors import CORS

# Local imports
from progress_sink import ProgressSink
from generate_recent_news import GenerateRecentNews
from search_term_generation import generate_search_terms
from websearch import perform_web_search
from crawling import perform_crawling
from identification_of_relevant_articles import identify_relevant_articles
from generation_of_most_impactful_news import generate_most_impactful_news
from utils import *

app = Flask(__name__)

# Configure CORS with specific settings for streaming
CORS(app, resources={
    r"/*": {
        "origins": "*",  # Allow all origins
        "methods": ["GET", "POST", "OPTIONS"],
        "allow_headers": ["Content-Type"],
        "expose_headers": ["Content-Type"],
        "supports_credentials": True,
        "max_age": 600
    }
})

# Add CORS headers to all responses
@app.after_request
def after_request(response):
    response.headers.add('Access-Control-Allow-Origin', '*')
    response.headers.add('Access-Control-Allow-Headers', 'Content-Type')
    response.headers.add('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
    #response.headers.add('Access-Control-Allow-Credentials', 'true')
    return response


def execute_pipeline_steps(query: str, sink: ProgressSink) -> GenerateRecentNews:
    """
    Executes all steps of the news generation pipeline for a single query.
    
    Args:
        query (str): The search query to process
        sink (ProgressSink): A sink for logging progress
    
    Returns:
        GenerateRecentNews: An object containing the generated news and all intermediary results
    """

    news_generation_pipeline_output = generate_search_terms(query=query, sink=sink)
    news_generation_pipeline_output = perform_web_search(recent_news=news_generation_pipeline_output, sink=sink)
    news_generation_pipeline_output = perform_crawling(recent_news=news_generation_pipeline_output, sink=sink)
    news_generation_pipeline_output = identify_relevant_articles(recent_news=news_generation_pipeline_output, sink=sink)
    news_generation_pipeline_output = generate_most_impactful_news(recent_news=news_generation_pipeline_output, sink=sink)
    return news_generation_pipeline_output
    

def run_pipeline(request_body: dict, queue: Queue) -> None:
    """
    Runs the pipeline for generating recent news about an input query.
    
    Args:
        request_body (dict): The initial news generation request containing the query
        queue (Queue): A queue for sending progress messages
    
    Returns:
        None
    """
    
    sink = ProgressSink(queue=queue)
    query = request_body['query']
    
    news_generation_pipeline_output = execute_pipeline_steps(query=query, sink=sink)
    sink.send_final(final_output=news_generation_pipeline_output._serialize_most_impactful_news())


def get_output_and_log_filenames(request_body: dict) -> dict:
    """
    Generates output and log filenames based on the input filename and current timestamp.
    
    Args:
        request_body (dict): The request containing input and optional output filenames
    
    Returns:
        dict: A dictionary containing the generated output and log filenames
    """

    input_filename = request_body['input_filename']
    base_output_filename = request_body.get('output_filename', input_filename.split('.txt')[0] + '-processed')
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d-%H:%M:%S")
    
    output_filename = f"{base_output_filename}-{timestamp}.txt"
    log_filename = f"{base_output_filename}-{timestamp}-logs.log"

    return {
        'output_filename': output_filename,
        'log_filename': log_filename
    }


def read_data(input_filename: str, n_rows: Union[str, None] = None) -> list[str]:
    """
    Reads data from a file and optionally limits the number of rows to process.
    
    Args:
        input_filename (str): The name of the file to read
        n_rows (Union[str, None], optional): Maximum number of rows to read. If None, reads all rows.
    
    Returns:
        list[str]: A list of queries read from the file
    
    Raises:
        FileNotFoundError: If the input file does not exist
        ValueError: If n_rows is not a valid integer
    """
    
    file_path = os.path.join('./data', input_filename)
    
    try:
        with open(file_path, "r") as f:
            data = [line.strip() for line in f if line.strip()]
            
        total_rows = len(data)
        if n_rows is None:
            log.info(msg=f'The input file has been read, it contains {total_rows} rows and all will be processed\n')
            return data
            
        try:
            n_rows_int = int(n_rows)
            if n_rows_int <= 0:
                raise ValueError("n_rows must be a positive integer")
                
            data_subset = data[:n_rows_int]
            log.info(msg=f'The input file has been read, it contains {total_rows} rows, {len(data_subset)} will be processed\n')
            return data_subset
            
        except ValueError as e:
            log.info(msg=f'Invalid n_rows value: {n_rows}\n')
            raise ValueError(f"n_rows must be a valid integer: {str(e)}")
            
    except FileNotFoundError:
        log.info(msg=f'File not found: {file_path}\n')
        raise FileNotFoundError(f"Input file does not exist: {file_path}")


def start_rate_limiters(max_search_requests_per_sec: int = 30, max_llm_requests_per_sec: int = 5) -> None:
    """
    Initializes and starts the rate limiters for search and LLM requests.
    
    Args:
        max_search_requests_per_sec (int, optional): Maximum search requests per second. Defaults to 30.
        max_llm_requests_per_sec (int, optional): Maximum LLM requests per second. Defaults to 5.
    
    Returns:
        None
    
    Raises:
        ValueError: If rate limits are not positive integers
    """
    if max_search_requests_per_sec <= 0 or max_llm_requests_per_sec <= 0:
        raise ValueError("Rate limits must be positive integers")
    
    # Only update if the values have changed
    current_search_limit = rate_limiter_search_requests.get_max_requests_per_sec()
    current_llm_limit = rate_limiter_llm_calls.get_max_requests_per_sec()
    
    if current_search_limit != max_search_requests_per_sec:
        rate_limiter_search_requests.update_max_requests_per_sec(max_requests_per_sec=max_search_requests_per_sec)
    
    if current_llm_limit != max_llm_requests_per_sec:
        rate_limiter_llm_calls.update_max_requests_per_sec(max_requests_per_sec=max_llm_requests_per_sec)
    
    # Log the current limits in a single statement
    log.info('Rate limiters configured: search={}/sec, llm={}/sec\n'.format(
        rate_limiter_search_requests.get_max_requests_per_sec(),
        rate_limiter_llm_calls.get_max_requests_per_sec()
    ))
    
    # Start background processes for both limiters
    processes = []
    for limiter in [rate_limiter_search_requests, rate_limiter_llm_calls]:
        process = Process(target=limiter.reset_count, daemon=True)
        process.start()
        processes.append(process)
    
    log.info('Started {} background processes for rate limiters\n'.format(len(processes)))


def process_batch(
    pipeline: Callable, 
    queries: list[str], 
    output_writer: FileWriter, 
    sink_summary_progress_messages: ProgressSink, 
    sink_detailed_progress_messages: ProgressSink, 
    in_parallel: bool = False
) -> list[GenerateRecentNews]:
    """
    Processes a batch of queries either sequentially or in parallel.
    
    Args:
        pipeline (Callable): The pipeline function to execute for each query
        queries (list[str]): List of queries to process
        output_writer (FileWriter): Writer for saving results
        sink_summary_progress_messages (ProgressSink): Sink for summary progress messages
        sink_detailed_progress_messages (ProgressSink): Sink for detailed progress messages
        in_parallel (bool, optional): Whether to process queries in parallel. Defaults to False.
    
    Returns:
        list[GenerateRecentNews]: List of results for each processed query
    
    Raises:
        ValueError: If queries list is empty
        Exception: If processing fails
    """

    if not queries:
        raise ValueError("Queries list cannot be empty")
    
    batch_processing_results = []
    log.info('Processing {} queries in {} mode\n'.format(
        len(queries), 
        'parallel' if in_parallel else 'sequential'
    ))

    # Configure rate limiters based on processing mode
    rate_limits = {
        'search': 10 if in_parallel else 30,
        'llm': 1 if in_parallel else 5
    }
    start_rate_limiters(
        max_search_requests_per_sec=rate_limits['search'],
        max_llm_requests_per_sec=rate_limits['llm']
    )

    def process_single_query(query: str) -> GenerateRecentNews:
        """Process a single query and handle timing/logging."""
        timestamp_start = get_and_log_current_time(
            message=f'Processing query "{query}" started',
            sink=sink_summary_progress_messages
        )
        
        pipeline_output = pipeline(query=query, sink=sink_detailed_progress_messages)
        
        output_writer.write(message=json.dumps({
            query: pipeline_output._serialize_most_impactful_news()
        }))
        
        get_and_log_current_time(
            message=f'Processing query "{query}" finished',
            sink=sink_summary_progress_messages
        )
        
        return pipeline_output

    if in_parallel:
        # Use a wrapper to capture results in parallel processing
        def parallel_wrapper(query, batch_processing_results):
            result = process_single_query(query)
            batch_processing_results.append(result)
            return result

        batch_processing_results = list(run_multiple_with_limited_time(
            func=parallel_wrapper,
            args=queries,
            max_time=None
        ))
    else:
        # Process queries sequentially
        for query in queries:
            result = process_single_query(query)
            batch_processing_results.append(result)

    return batch_processing_results


def get_statistics(batch_processing_results: list[GenerateRecentNews]) -> dict:
    """
    Generates statistics about the batch processing results.
    
    Args:
        batch_processing_results (list[GenerateRecentNews]): List of results from batch processing
    
    Returns:
        dict: Statistics about the processing results 
    """
    
    return {
        'number_of_outputs': len(batch_processing_results),
        'number_of_search_terms': [len(result.search_terms) for result in batch_processing_results],
        'number_of_retrieved_urls': [len(result.retrieved_urls) for result in batch_processing_results],
        'number_of_parsed_urls': [len(result.parsed_urls) for result in batch_processing_results],
        'number_of_relevant_articles': [len(result.relevant_articles) for result in batch_processing_results],
        'number_of_chars_in_most_impactful_news': [
            sum(len(news.news_summary) for news in result.most_impactful_news) 
            for result in batch_processing_results
        ]
    }


def run_pipeline_batch(request_body: dict, queue: Queue) -> None:
    """
    Runs the pipeline for generating recent news about queries in a file.
    
    Args:
        request_body (dict): The initial news generation request containing file information
        queue (Queue): A queue for sending progress messages
    
    Returns:
        None
    
    Raises:
        ValueError: If input_filename is missing or invalid
        Exception: For any other processing errors
    """
    if not request_body or not request_body.get('input_filename'):
        raise ValueError("Missing or invalid input_filename in request body")
    
    sink = ProgressSink(queue=queue)
    output_writer = None
    
    try:
        # Setup detailed progress tracking
        message_queue_detailed_progress_messages = Queue()
        sink_detailed_progress_messages = ProgressSink(queue=message_queue_detailed_progress_messages)
        
        input_filename = request_body['input_filename']
        
        # Log start time
        timestamp_start = get_and_log_current_time(
            message=f'Processing file "{input_filename}" started',
            sink=sink
        )
        
        # Setup GCS and download file
        authenticate_gcs()
        download_from_gcs(source_filename=input_filename)
        
        # Read and process queries
        queries = read_data(
            input_filename=input_filename,
            n_rows=request_body.get('n_rows', None)
        )
        
        if not queries:
            raise ValueError(f"No valid queries found in file {input_filename}")
        
        # Setup output files
        filenames = get_output_and_log_filenames(request_body=request_body)
        output_filename = filenames['output_filename']
        log_filename = filenames['log_filename']
        
        output_writer = FileWriter(filename=os.path.join('./data', output_filename))
        
        # Process batch
        batch_processing_results = process_batch(
            pipeline=execute_pipeline_steps,
            queries=queries,
            output_writer=output_writer,
            sink_summary_progress_messages=sink,
            sink_detailed_progress_messages=sink_detailed_progress_messages,
            in_parallel=request_body.get('in_parallel', False)
        )
        
        # Send statistics
        batch_processing_statistics = get_statistics(batch_processing_results=batch_processing_results)
        sink.send(message=batch_processing_statistics)
        
        # Close output writer before upload
        if output_writer:
            output_writer.close()
        
        # Upload results to GCS
        upload_to_gcs(
            source_filename=os.path.join('./data', output_filename),
            destination_filename=output_filename
        )
        upload_to_gcs(
            source_filename=LOG_FILENAME,
            destination_filename=log_filename
        )
        
        # Log completion
        timestamp_end = get_and_log_current_time(
            message=f'Processing file "{input_filename}" finished',
            sink=sink
        )
        log_processing_duration(
            timestamp_start=timestamp_start,
            timestamp_end=timestamp_end,
            message=f'Processing file "{input_filename}"',
            sink=sink
        )
        
        # Send final success message
        sink.send_final(final_output={
            'status_code': 200,
            'output_filename': output_filename
        })
        
    except Exception as e:
        # Ensure resources are cleaned up
        if output_writer:
            output_writer.close()
        sink.close()
        log.error(f"Error processing batch: {str(e)}")
        raise


def stream_pipeline(request_body: dict, run_pipeline: Callable) -> Generator:
    """
    Runs the pipeline and streams the messages sent by the pipeline to the sink.
    
    Args:
        request_body (dict): The initial news generation request
        run_pipeline (Callable): The pipeline function to execute
    
    Returns:
        Generator: A stream of progress messages for the recent news generation pipeline
    """
    
    message_queue = Queue()

    generation_thread = threading.Thread(
        target=run_pipeline,
        args=(request_body, message_queue,)
    )

    generation_thread.start()
    
    while True:
        msg = message_queue.get()
        if msg is None:
            break
        yield msg
        
    generation_thread.join()


@app.route("/health_check", methods=["POST"])
def health_check() -> tuple[str, int, dict]:
    """
    Health check endpoint that verifies the service is running.
    
    Returns:
        tuple[str, int, dict]: Response message, status code, and headers
    """
    data = request.get_json()
    if not data or "query" not in data:
        return json.dumps({"error": "Missing 'query' in request body"}), 400, {"Content-Type": "application/json"}

    query = data['query']
    return json.dumps({"message": "Request {} was successful!".format(query)}), 200, {"Content-Type": "application/json"}


@app.route("/health_check_streaming", methods=["POST"])
def health_check_streaming():
    data = request.get_json()
    if not data or 'query' not in data:
        return json.dumps({"error": "Missing 'query' in request body"}), 400, {"Content-Type": "application/json"}

    query = data['query']

    def stream_health_check(query):
        yield 'Request' + '\n'
        yield query + '\n'
        yield 'was successful!' + '\n'

    return stream_health_check(query)
    #return Response(stream_with_context(stream_health_check(query)), content_type = "text/plain")


@app.route("/generate_recent_news", methods=["POST", "OPTIONS"])
def generate_recent_news():
    if request.method == "OPTIONS":
        return "", 200

    request_body = request.get_json()
    if not request_body or len(request_body.get('query', '')) <= 1:
        return json.dumps({"error": "Missing 'query' in request body"}), 400, {"Content-Type": "application/json"}

    start_rate_limiters(
        max_search_requests_per_sec=30,
        max_llm_requests_per_sec=5
    )

    def generate():
        for message in stream_pipeline(request_body, run_pipeline):
            yield f"{json.dumps(message)}\n"

    return Response(
        stream_with_context(generate()),
        mimetype='application/json',
        headers={
            'Cache-Control': 'no-cache',
            'Connection': 'keep-alive',
            'Content-Type': 'application/json',
            'X-Accel-Buffering': 'no'
        }
    )


@app.route("/generate_recent_news_batch", methods=["POST", "OPTIONS"])
def generate_recent_news_batch():
    if request.method == "OPTIONS":
        return "", 200

    request_body = request.get_json()
    if not request_body or len(request_body.get('input_filename', '')) <= 1:
        return json.dumps({"error": "Missing 'input_filename' in request body"}), 400, {"Content-Type": "application/json"}  

    def generate():
        for message in stream_pipeline(request_body, run_pipeline_batch):
            yield f"{json.dumps(message)}\n"

    return Response(
        stream_with_context(generate()),
        mimetype='application/json',
        headers={
            'Cache-Control': 'no-cache',
            'Connection': 'keep-alive',
            'Content-Type': 'application/json',
            'X-Accel-Buffering': 'no'
        }
    )
    
    
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)