import urllib.request
import ssl
import os

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

pages = [
    'home', 'posthp', 'vg', 'vrg', 'dist', 'aoi', 'point', 'laoi', 'route', 'geoid', 'api',
    'getdistcode', 'getstatcode', 'getlucode'
]

os.makedirs('scratch/bhuvan_docs', exist_ok=True)

for p in pages:
    url = f"https://bhuvan-app1.nrsc.gov.in/api/get/{p}.php"
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
    try:
        with urllib.request.urlopen(req, context=ctx, timeout=10) as resp:
            content = resp.read().decode('utf-8', errors='ignore')
            with open(f"scratch/bhuvan_docs/{p}.html", "w", encoding="utf-8") as f:
                f.write(content)
            print(f"Downloaded {p}: {len(content)} bytes")
    except Exception as e:
        print(f"Error {p}: {e}")
