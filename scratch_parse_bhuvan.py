import re

with open("scratch_bhuvan_api.html", encoding="utf-8") as f:
    text = f.read()

# Let's extract script blocks
scripts = re.findall(r'<script\b[^>]*>(.*?)</script>', text, re.DOTALL | re.IGNORECASE)
for idx, s in enumerate(scripts):
    if len(s.strip()) > 0:
        print(f"=== SCRIPT BLOCK {idx} ({len(s)} chars) ===")
        print(s[:3000]) # print up to 3000 chars
