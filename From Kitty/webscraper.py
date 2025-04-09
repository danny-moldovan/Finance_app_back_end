import requests
from bs4 import BeautifulSoup
from typing import Optional
from urllib.parse import quote_plus
import os
# No imports needed for print statements


webscraper_tool = {
    "type": "function",
    "function": {
        "name": "scrape_webpage",
        "description": "Scrape and extract text content from a webpage given its URL.",
        "parameters": {
            "type": "object",
            "properties": {
                "url": {
                    "type": "string",
                    "description": "The URL of the webpage to scrape"
                },
            },
            "required": ["url"],
            "additionalProperties": False
        },
        "strict": True
    }
}

def get_crawlbase_error_description(pc_status: int) -> str:
    """Get detailed description for CrawlBase pc_status codes."""
    error_codes = {
        500: "Internal error - please try again",
        501: "Not implemented - feature not available",
        502: "Bad gateway - invalid response from upstream",
        503: "Service unavailable - server overloaded",
        504: "Gateway timeout - request timed out",
        505: "HTTP version not supported",
        520: "Unknown error",
        521: "Web server is down",
        522: "Connection timed out",
        523: "Origin is unreachable",
        524: "A timeout occurred",
        525: "SSL handshake failed",
        526: "Invalid SSL certificate",
        527: "Railgun error",
        530: "Origin DNS error",
        599: "Network connect timeout error"
    }
    return error_codes.get(pc_status, "Unknown error code")

def scrape_webpage(url: str) -> str:
    """
    Scrape and extract text content from a webpage using CrawlBase API.
    
    Args:
        url: The URL of the webpage to scrape
    
    Returns:
        A string containing the extracted text content
    """
    CRAWLBASE_TOKEN = os.getenv('CRAWLBASE_TOKEN')
    CRAWLBASE_JS_TOKEN = os.getenv('CRAWLBASE_JS_TOKEN')
    
    if not CRAWLBASE_TOKEN:
        return "Error: CrawlBase token not configured"
    if not CRAWLBASE_JS_TOKEN:
        return "Error: CrawlBase JS token not configured"

    try:
        encoded_url = quote_plus(url)
        print(f"Attempting to scrape URL: {url}")

        # First try with regular token
        api_url = f"https://api.crawlbase.com/?token={CRAWLBASE_TOKEN}&url={encoded_url}"
        print("Making request with regular token")
        
        response = requests.get(api_url, timeout=90)
        
        # Log response headers for debugging
        pc_status = response.headers.get('pc_status')
        original_status = response.headers.get('original_status')
        print(f"Response status: {response.status_code}")
        print(f"CrawlBase pc_status: {pc_status}")
        print(f"Original status: {original_status}")

        # If we get a 403 or no content, try with JS token
        if (response.status_code in [403, 520] or not response.text.strip()) and CRAWLBASE_JS_TOKEN:
            print("Regular token failed, trying with JS token")
            api_url = f"https://api.crawlbase.com/?token={CRAWLBASE_JS_TOKEN}&url={encoded_url}"
            response = requests.get(api_url, timeout=90)
            
            # Log JS token response
            pc_status = response.headers.get('pc_status')
            original_status = response.headers.get('original_status')
            print(f"JS token response status: {response.status_code}")
            print(f"JS token pc_status: {pc_status}")
            print(f"JS token original status: {original_status}")

        # Handle CrawlBase specific error codes
        if response.status_code == 520:
            pc_status_code = int(pc_status) if pc_status and pc_status.isdigit() else 520
            error_desc = get_crawlbase_error_description(pc_status_code)
            print(f"CrawlBase error: {error_desc} (PC Status: {pc_status_code})")
            return f"Error: CrawlBase request failed - {error_desc}"

        response.raise_for_status()

        # Parse HTML content
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Remove unwanted elements
        for element in soup(["script", "style", "iframe", "nav", "footer", "noscript"]):
            element.decompose()
        
        # Get text content
        text = soup.get_text(separator='\n')

        print("--------------------------------")
        print(text)
        print("--------------------------------")
        
        # Clean up text
        lines = []
        for line in text.splitlines():
            line = line.strip()
            if line and len(line) > 1:
                lines.append(line)
        
        text = '\n'.join(lines)
        
        
        print(f"Successfully scraped content (length: {len(text)})")
        return text if text.strip() else "No text content found on the webpage"

    except requests.Timeout:
        print("Request timeout error")
        return "Error: Request timed out while accessing the webpage"
    except requests.RequestException as e:
        print(f"Request exception: {str(e)}")
        if isinstance(e, requests.exceptions.HTTPError):
            if e.response.status_code == 403:
                return "Error: Access forbidden (403) - Website may be blocking access"
            return f"Error: HTTP {e.response.status_code} error occurred"
        return f"Error scraping webpage: {str(e)}"
    except Exception as e:
        print(f"Unexpected error: {str(e)}")
        return f"Error processing webpage content: {str(e)}" 