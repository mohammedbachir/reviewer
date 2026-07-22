import os, json
from dotenv import load_dotenv
load_dotenv()
from curl_cffi import requests

sb = os.environ.get("SUPABASE_URL","")
sk = os.environ.get("SUPABASE_SERVICE_ROLE_KEY","")
h = {"apikey":sk,"Authorization":f"Bearer {sk}"}

r = requests.get(f"{sb}/rest/v1/businesses?select=id,name,firebase,archive,api_keys,crtsh,sherlock&limit=5", headers=h)
data = r.json()
for d in data[:3]:
    print(json.dumps(d, indent=2, default=str))
    print("---")
