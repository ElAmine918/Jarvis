import httpx
import os
import asyncio
from dotenv import load_dotenv

load_dotenv('/Users/amine/Code/MyCloud/.env')

async def main():
    api_key = os.getenv('GEMINI_API_KEY')
    if not api_key:
        print("NO API KEY")
        return
    url = "https://generativelanguage.googleapis.com/v1beta/models"
    async with httpx.AsyncClient() as client:
        resp = await client.get(url + f"?key={api_key}")
        print(resp.status_code)
        if resp.status_code == 200:
            for m in resp.json().get('models', []):
                print(m['name'])
        else:
            print(resp.text)

asyncio.run(main())
