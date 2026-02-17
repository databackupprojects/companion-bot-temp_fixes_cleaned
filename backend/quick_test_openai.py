#!/usr/bin/env python3
"""
Quick OpenAI API Test - Fast diagnosis of 429 errors
"""

import os
import asyncio
from dotenv import load_dotenv
from openai import AsyncOpenAI
import sys

load_dotenv()

async def quick_test():
    """Quick test of OpenAI API"""
    
    api_key = os.getenv("LLM_API_KEY") or os.getenv("OPENAI_API_KEY")
    model = os.getenv("OPENAI_MODEL", "gpt-4")
    
    print(f"Testing OpenAI API...")
    print(f"  Model: {model}")
    print(f"  API Key: {api_key[:20]}..." if api_key else "  API Key: NOT FOUND")
    print()
    
    if not api_key:
        print("❌ ERROR: No API key in environment")
        sys.exit(1)
    
    try:
        client = AsyncOpenAI(api_key=api_key)
        
        print("📤 Sending request...")
        response = await client.chat.completions.create(
            model=model,
            messages=[
                {"role": "user", "content": "Say 'Success' only."}
            ],
            max_tokens=10
        )
        
        print(f"✅ SUCCESS!")
        print(f"   Response: {response.choices[0].message.content}")
        print(f"   Usage: {response.usage.prompt_tokens} prompt + {response.usage.completion_tokens} completion = {response.usage.total_tokens} total")
        
    except Exception as e:
        print(f"❌ ERROR: {type(e).__name__}")
        print(f"   {str(e)}")
        
        # Print error details
        if hasattr(e, 'status_code'):
            print(f"\n   Status Code: {e.status_code}")
        
        if hasattr(e, 'headers'):
            print(f"\n   Response Headers:")
            for k, v in e.headers.items():
                print(f"     {k}: {v}")
        
        if hasattr(e, 'response'):
            if hasattr(e.response, 'text'):
                print(f"\n   Response Body: {e.response.text}")

if __name__ == "__main__":
    asyncio.run(quick_test())
