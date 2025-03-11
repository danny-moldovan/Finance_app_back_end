import requests
import os
import json
from dotenv import load_dotenv
from bs4 import BeautifulSoup 
import datetime
import time
from time import sleep
from multiprocessing import Process, Manager
from google import genai
from duckduckgo_search import DDGS
from flask import Flask, request, Response, stream_with_context, jsonify
#from flask_caching import Cache
from search_term_generation import *
from websearch import *
from webpage_retrieval import *
from identification_of_relevant_articles import *
from aggregated_answer_generation import *
from utils import *
from cache import cache

app = Flask(__name__)

app.config['CACHE_TYPE'] = 'filesystem'
app.config['CACHE_DIR'] = '/teamspace/studios/this_studio/back_end/flask_cache'
app.config['CACHE_DEFAULT_TIMEOUT'] = 60 * 60 * 24 * 10 #10 days in seconds
cache.init_app(app)
#manual_cache_dir = '/teamspace/studios/this_studio/back_end/manual_cache'

serialized_results_filename = '/teamspace/studios/this_studio/back_end/serialized_results.txt'

load_dotenv()

def get_summary_about_search_term(query, output_filename = serialized_results_filename):
    complete_results = {}

    processing_start = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S") 
    complete_results['processing_start'] = json.dumps(processing_start)
    log.info("The processing of the search term {} started at {}.".format(query, processing_start))
    log.info('')
    
    term_of_interest_meaning = None
    
    all_search_terms_stream = generate_search_terms(query)

    all_search_terms_list = []
    
    for message in all_search_terms_stream:
        return_type, return_value = parse_message_sent(message)
        if return_type == "log":
            yield message
        elif term_of_interest_meaning is None:
            term_of_interest_meaning = return_value
            yield value_message("Term meaning: {}".format(term_of_interest_meaning))
        else:
            yield message
            all_search_terms_list.append(return_value)
            #sleep(0.1)

    complete_results['term_of_interest_meaning'] = term_of_interest_meaning
    complete_results['all_search_terms'] = all_search_terms_list
    
    agg_search_results_list = []

    agg_search_results_stream = search_web(all_search_terms_list)
    
    for message in agg_search_results_stream:
        return_type, return_value = parse_message_sent(message)
        if return_type == "value":
            agg_search_results_list.append(return_value)
        else:
            yield message

    complete_results['agg_search_results'] = agg_search_results_list

    extracted_content_from_search_results_stream = extract_content_from_search_results(agg_search_results_list)

    extracted_content_from_search_results = {}

    for message in extracted_content_from_search_results_stream:
        return_type, return_value = parse_message_sent(message)
        if return_type == "value":
            for url in return_value.keys():
                extracted_content_from_search_results[url] = return_value[url]
        else:
            yield message

    complete_results['extracted_content_from_search_results'] = extracted_content_from_search_results
    
    summary_completions_stream = generate_summary_completions(term_of_interest_meaning, extracted_content_from_search_results)
    
    summary_completions = []
    
    for message in summary_completions_stream:
        return_type, return_value = parse_message_sent(message)
        if return_type == "value":
            summary_completions.append(return_value)
            #print(return_value)
            #print()
        else:
            yield message

    complete_results['summary_completions'] = summary_completions
    
    final_output_stream = generate_aggregated_output(term_of_interest_meaning, summary_completions, extracted_content_from_search_results)

    final_output_list = []
    
    for message in final_output_stream:
        return_type, return_value = parse_message_sent(message)
        if return_type == "value":
            final_output_list.append(return_value)    
        yield message

    complete_results['final_output'] = final_output_list

    processing_end = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S") 
    complete_results['processing_end'] = json.dumps(processing_end)
    log.info("The processing of the search term {} finished at {}.".format(query, processing_end))
    log.info('')

    yield value_message({'complete_results': complete_results})
    
    with open(output_filename, "a") as f:  # Open in append mode
        f.writelines([json.dumps({query: complete_results}) + '\n'])


@app.route("/generate_summary", methods=["POST"])
def generate_summary():
    data = request.get_json()
    if not data or "query" not in data:
        return json.dumps({"error": "Missing 'query' in request body"}), 400, {"Content-Type": "application/json"}

    query = data["query"]
    return Response(stream_with_context(get_summary_about_search_term(query)), content_type = "text/plain")
    #return Response(QUERY_UNDERSTANDING_PROMPT_TEMPLATE.format(" ", " "), content_type="text/plain")


@app.route("/generate_batch_summary", methods=["POST"])
def generate_batch_summary():
    data = request.get_json()
    if not data or "filename" not in data:
        return json.dumps({"error": "Missing 'filename' in request body"}), 400, {"Content-Type": "application/json"}

    input_filename = data["filename"]
    full_input_filename = os.path.join('./data', input_filename)
    
    '''
    with open(full_input_filename, "r") as f:
        input_data = f.readlines()

    output_data = input_data  #TODO: implement the logic
    output_filename = input_filename.split('.txt')[0] + '_processed.txt'
    full_output_filename = os.path.join('./data', output_filename)

    with open(full_output_filename, "w") as f:
        f.writelines([line + "\n" for line in output_data])
    '''

    processing_result = process_file(full_input_filename)

    if processing_result == "Request was successful":
        return jsonify({"message": "Request was successful!"}), 200, {"Content-Type": "application/json"}
    else:
        return json.dumps({"error": "Missing 'filename' in request body"}), 400, {"Content-Type": "application/json"}


def process_file(input_filename):
    log.info('Started processing the file')
    log.info('')
    
    if not input_filename:
        return "Error: missing 'filename' in request body"

    full_input_filename = os.path.join('./data', input_filename)
    with open(full_input_filename, "r") as f:
        input_data = f.readlines()

    log.info('The file has been read and it has {} lines'.format(len(input_data)))
    log.info('')

    output_filename = input_filename.split('.txt')[0] + '_processed.txt'
    full_output_filename = os.path.join('./data', output_filename)
    log.info('Output filename: {}'.format(full_output_filename))
    log.info('')

    n_rows = 3

    output_data = []
    
    for row in input_data[:n_rows]:
        processed_row = ''
        message_stream = get_summary_about_search_term(row.split('\n')[0], full_output_filename)        
        for m in message_stream:
            processed_row += m + '\n'

        output_data.append({row: processed_row})
        #print({row: processed_row})
        
    #with open(full_output_filename, "w") as f:
    #    f.writelines([json.dumps(row) for row in output_data])

    return "Request was successful"


if __name__ == "__main__":
    app.run(host = "0.0.0.0", port = 5000, debug = True)
