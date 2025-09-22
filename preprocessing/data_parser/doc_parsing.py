# pip install requests
import requests
import json
import os
from dotenv import load_dotenv
 
load_dotenv()
api_key = os.getenv("UPSTAGE_API_KEY")  # ex: up_xxxYYYzzzAAAbbbCCC
filename = ".\\data\\tag_code\\manual.pdf"  # ex: ./image.png
 
url = "https://api.upstage.ai/v1/document-digitization"
headers = {"Authorization": f"Bearer {api_key}"}
files = {"document": open(filename, "rb")}
data = {"ocr": "force", "base64_encoding": "['table']", "model": "document-parse"}
response = requests.post(url, headers=headers, files=files, data=data)
 
result_dir = os.path.join(os.path.dirname(__file__), 'result')
os.makedirs(result_dir, exist_ok=True)
output_path = os.path.join(result_dir, f"{os.path.splitext(os.path.basename(filename))[0]}.json")
with open(output_path, 'w', encoding='utf-8') as fp:
    json.dump(response.json(), fp, ensure_ascii=False, indent=2)