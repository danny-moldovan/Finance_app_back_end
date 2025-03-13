from bs4 import BeautifulSoup 
import requests
import time
from utils import *

def processWebpage(url):
    try:
        print('Extracting {}'.format(url))
        response = requests.get(url)
        soup = BeautifulSoup(response.text, 'html.parser') 
        all_tags = soup.find_all() #soup.find_all()
    
        all_text = list()
        for tag in all_tags:
            paragraphs = tag.find_all('p')
            for p in paragraphs:
                p_cleaned = ''.join(i.strip() for i in p.get_text().split('\n'))
                all_text.append(p_cleaned)
    
        all_text_deduplicated = set(all_text)
        #print('Extracted content: {}.'.format(join(all_text_deduplicated)))
    
        return ' '.join(all_text_deduplicated)
    except Exception as e:
        #print('Exception occured for the URL: {}'.format(url))
        return ''

url = 'https://www.msn.com/en-us/money/markets/us-inflation-cooled-in-february-but-trump-s-tariff-plans-and-trade-war-loom/ar-AA1ALxHz'

print(processWebpage(url))