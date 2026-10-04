import requests
from requests.auth import HTTPBasicAuth

url = 'http://localhost:8080/admin/api/data'
try:
    response = requests.get(url, auth=HTTPBasicAuth('admin', 'chpECSBQurWF6zhvw_lps-kJ6ZOsyDUP'))
    print("Status code:", response.status_code)
    print("Response:", response.text[:200])
except Exception as e:
    print("Error:", e)
