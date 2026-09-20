import urllib.request, ssl, re

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE
req = urllib.request.Request('https://bhuvan-app1.nrsc.gov.in/iwmp/index.php', headers={'User-Agent': 'Mozilla/5.0'})
try:
    with urllib.request.urlopen(req, context=ctx) as r:
        html = r.read().decode('utf-8', errors='ignore')
    
    with open('scratch/iwmp_index.html', 'w', encoding='utf-8') as f:
        f.write(html)
    
    print('Saved scratch/iwmp_index.html, length:', len(html))
    
    srcs = re.findall(r'<script[^>]+src=["\'](.*?)["\']', html)
    print('External scripts:', srcs)
    
    # Check projid options
    proj_options = re.findall(r'<option\s+value=["\'](.*?)["\']>(.*?)</option>', html)
    print('Options count:', len(proj_options))
    print('First 10 options:', proj_options[:10])
except Exception as e:
    print('Error:', e)

