import urllib.request
import urllib.error

try:
    url = "http://127.0.0.1:8000/jobs/discover?query=backend"
    print(f"Fetching {url}")
    req = urllib.request.Request(url)
    with urllib.request.urlopen(req) as response:
        print("Success:", response.read())
except urllib.error.HTTPError as e:
    print("HTTP Error:", e.code)
    print("Body:", e.read().decode('utf-8'))
except Exception as e:
    print("Other Error:", e)

