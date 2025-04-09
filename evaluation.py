import json
import logging
import os

log = logging.getLogger('logger')
log.propagate = True
log.setLevel(logging.DEBUG)
formatter = logging.Formatter('%(message)s')

file_handler = logging.FileHandler('evaluation_logs.log', mode = 'w', encoding = 'utf-8')
file_handler.setLevel(logging.DEBUG)
file_handler.setFormatter(formatter)
log.addHandler(file_handler)

if __name__ == "__main__":
    log.info('Evaluation started\n')
    
    try:
        current_file = '/workspace/evaluation_response_current.json'
        new_file = '/workspace/evaluation_response_new.json'
        
        if not os.path.exists(current_file):
            log.info(f'Error: File {current_file} does not exist')
        else:
            with open(current_file, "r") as file:
                evaluation_response_current = [line.strip() for line in file if line.strip()]
                log.info('Evaluation before deployment:\n')
                log.info(evaluation_response_current)
            
        if not os.path.exists(new_file):
            log.info(f'Error: File {new_file} does not exist')
        else:
            with open(new_file, "r") as file:
                evaluation_response_new = [line.strip() for line in file if line.strip()]
                log.info('Evaluation after deployment:\n')
                log.info(evaluation_response_new)
        
        log.info('Evaluation finished successfully\n')

    except Exception as e:
        log.info('Error: {}\n'.format(e))
