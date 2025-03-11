from google import genai
from dotenv import load_dotenv
import os

load_dotenv()

gemini_client = genai.Client(api_key = os.getenv('GEMINI_API_KEY'), http_options = {'api_version' : 'v1alpha'})
#print('Gemini client initialised')