import asyncio
import os

from dotenv import load_dotenv
from browser_use import Agent, ChatOpenAI

load_dotenv()


async def main():
    llm = ChatOpenAI(
        model="auto",
        base_url="http://127.0.0.1:31415/v1",
        api_key=os.getenv("FREELLMAPI_API_KEY"),
        temperature=0.0,
    )

    agent = Agent(
        task="""
        go to youtube

        """,
        llm=llm,
    )

    result = await agent.run()

    print("\n===== RESULT =====")
    print(result)


if __name__ == "__main__":
    asyncio.run(main())