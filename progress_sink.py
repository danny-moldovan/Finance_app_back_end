import json
#import queue
from multiprocessing import Queue
from typing import *
import time

SINK_FINAL_MESSAGE_TYPE = "final"

class ProgressSink:
    def __init__(self, queue: Queue):
        self.messages = []
        self.queue = queue
    
    def send(self, message: Any, message_type: str = "progress") -> None:
        """Add a progress message to the sink"""
        self.queue.put(json.dumps({"message_type": message_type, "message": message}) + "\n")
    
    def send_final(self, final_output: Any) -> None:
        """Send final message and close the sink"""
        self.send(message=final_output, message_type=SINK_FINAL_MESSAGE_TYPE)
        self.close()
    
    def close(self) -> None:
        """Close the sink by sending None to the queue"""
        self.queue.put(None)
