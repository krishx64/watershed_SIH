import urllib.request, ssl, re

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

for js_name in ['lib/iwmp_03052019.js', 'lib/added.js']:
    url = f'https://bhuvan-app1.nrsc.gov.in/iwmp/{js_name}'
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
    try:
        with urllib.request.urlopen(req, context=ctx) as r:
            js = r.read().decode('utf-8', errors='ignore')
        matches = re.findall(r'.{0,60}photo.{0,60}', js, re.IGNORECASE)
        print(f"File {js_name} ({len(js)} bytes) has {len(matches)} photo matches:")
        for m in matches[:5]:
            print("  *", m.strip())
    except Exception as e:
        print(f"Error {js_name}: {e}")
