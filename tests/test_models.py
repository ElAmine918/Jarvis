import asyncio
import os
import sys

sys.path.append('/Users/amine/Code/MyCloud/jarvis')
from jarvis.core.router import get_dynamic_gemini_models

async def main():
    api_key = "REDACTED_API_KEY"
    primary_model = "gemini-3.5-flash"
        
    models = await get_dynamic_gemini_models(api_key, primary_model)
    print("MODELS:")
    for i, m in enumerate(models):
        print(f"{i+1}. {m}")

asyncio.run(main())
