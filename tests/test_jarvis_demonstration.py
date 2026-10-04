import asyncio
import os
from jarvis.core.agent import JarvisAgent

async def main():
    agent = JarvisAgent()
    await agent.init()
    
    messages = [
        {"role": "user", "content": "Salut Jarvis, révise ce code s'il te plaît : print('hello world')"}
    ]
    
    print("🤖 Jarvis est en train d'analyser la requête (avec la skill Code Review activée)...")
    
    async for chunk in agent.process_message(messages, "jarvis-ollama", "test_session"):
        print(chunk, end="", flush=True)
    print("\n")

if __name__ == "__main__":
    asyncio.run(main())
