import diskcache as dc
import os

# Create cache directory if it doesn't exist
cache_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "cache")
os.makedirs(cache_dir, exist_ok=True)

cache = dc.Cache(cache_dir)
TTL = 3600 #1 hour in seconds