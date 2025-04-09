import diskcache as dc

cache = dc.Cache("./cache") 

test_url = 'https://www.moneycontrol.com/news/business/usha-vance-wife-of-us-vice-president-vance-to-make-high-profile-visit-to-greenland-12972946.html'
prefix = "('United States Dollar', 'final_output')"

for k in list(cache.iterkeys()):
    if prefix in k:
        print('{}: {}'.format(k, len(cache.get(k))))
        print()
