from openai import AsyncOpenAI
import asyncio
import os
from openai import AsyncOpenAI
client = AsyncOpenAI(api_key="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")

async def test_gpt():
    response = await client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[{"role": "user", "content": "안녕 GPT, 잘 작동하니?"}]
    )
    print(response.choices[0].message.content)

asyncio.run(test_gpt())