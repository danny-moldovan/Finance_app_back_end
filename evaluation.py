import json
import logging

#log = logging.getLogger('logger')
#log.setLevel(logging.DEBUG)

if __name__ == "__main__":
    print('Evaluation started')
    
    try:
        with open('/workspace/evaluation_response_current.json', "r") as file:
            evaluation_response_current = json.load(file)

        with open('/workspace/evaluation_response_new.json', "r") as file:
            evaluation_response_new = json.load(file)
        
        print(evaluation_response_current)
        print(evaluation_response_new)

        print('Evaluation finished successfully')

    except Exception as e:
        print('Error: {}'.format(e))
