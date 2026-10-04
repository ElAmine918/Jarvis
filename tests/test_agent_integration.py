import asyncio
from jarvis.core.agent import JarvisAgent

async def main():
    agent = JarvisAgent()
    
    # Simulate a user message triggering the skill
    messages = [
        {"role": "user", "content": "Salut Jarvis, révise ce code s'il te plaît : print('hello')"}
    ]
    
    history = agent._prepare_history(messages, session_id="test")
    
    system_prompt = history[0]["content"]
    print("=== SYSTEM PROMPT ===")
    print(system_prompt)
    print("=====================")
    
    if "code review" in system_prompt.lower() or "workflow" in system_prompt.lower():
        print("✅ Skill successfully injected!")
    else:
        print("❌ Skill injection failed.")
        
    if "tu dois être poli" in system_prompt.lower():
        print("✅ Rule successfully injected!")
    else:
        print("❌ Rule injection failed.")

if __name__ == "__main__":
    asyncio.run(main())
