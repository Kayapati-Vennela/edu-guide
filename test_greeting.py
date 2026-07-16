import asyncio
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types

from app.agent import root_agent

async def main():
    session_service = InMemorySessionService()
    session = await session_service.create_session(user_id="test_user", app_name="test")
    runner = Runner(agent=root_agent, session_service=session_service, app_name="test")
    
    message = types.Content(
        role="user", parts=[types.Part.from_text(text="Hi!")]
    )
    
    print("Running agent with 'Hi!'...")
    async for event in runner.run_async(
        new_message=message,
        user_id="test_user",
        session_id=session.id,
    ):
        print(f"Event: {event}")
        if hasattr(event, 'content') and event.content:
            print(f"  Content: {event.content}")
        if hasattr(event, 'actions') and event.actions:
            print(f"  Actions: {event.actions}")
            
    # Get updated session
    updated_session = await session_service.get_session(
        app_name="test", user_id="test_user", session_id=session.id
    )
    print(f"Final State: {updated_session.state}")

if __name__ == "__main__":
    asyncio.run(main())
