import os
import requests
from typing import Optional

websearch_tool = {
    "type": "function",
    "function": {
        "name": "search_web",
        "description": "Search the web using Brave Search API.",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "The search query term"
                },
                "count": {
                    "type": "integer",
                    "description": "Number of results to return (max 20, defaults to 5)"
                }
            },
            "required": ["query", "count"],
            "additionalProperties": False
        },
        "strict": True
    }
}

def search_web(query: str, count: Optional[int] = 5) -> str:
    """
    Perform a web search using Brave Search API.
    
    Args:
        query: The search query term
        count: Number of results to return (default 5, max 20)
    
    Returns:
        A formatted string containing the search results
    """
    # Ensure count is within valid range
    count = min(max(1, count), 20)
    
    # Get API key from environment variable
    api_key = os.getenv("BRAVE_SEARCH_API_KEY")
    if not api_key:
        raise ValueError("BRAVE_SEARCH_API_KEY environment variable not set")

    headers = {
        "Accept": "application/json",
        "Accept-Encoding": "gzip",
        "X-Subscription-Token": api_key
    }

    params = {
        "q": query,
        "count": count
    }

    try:
        response = requests.get(
            "https://api.search.brave.com/res/v1/web/search",
            headers=headers,
            params=params
        )
        response.raise_for_status()
        
        data = response.json()
        
        # Extract and format web results
        if "web" not in data or "results" not in data["web"]:
            return "No results found"
            
        results = []
        for result in data["web"]["results"][:count]:
            title = result.get("title", "No title")
            url = result.get("url", "No URL")
            description = result.get("description", "No description")
            results.append(f"Title: {title}\nURL: {url}\nDescription: {description}\n")

        return "\n".join(results)

    except requests.RequestException as e:
        return f"Error performing web search: {str(e)}" 