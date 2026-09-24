"""Cloud avatar agent -- connect a bitHuman avatar to LiveKit with OpenAI voice.

Setup:
    export BITHUMAN_API_SECRET=your_secret
    export BITHUMAN_AGENT_ID=your_agent_code     # from www.bithuman.ai
    export LIVEKIT_URL=wss://your-livekit-server
    export LIVEKIT_API_KEY=...
    export LIVEKIT_API_SECRET=...
    export OPENAI_API_KEY=...

    pip install -r requirements.txt
    python cloud-avatar.py dev
"""

import os

import aiohttp
from livekit.agents import Agent, AgentSession, JobContext, RoomOutputOptions, WorkerOptions, WorkerType, cli
from livekit.plugins import bithuman, openai, silero
from openai.types.realtime.realtime_audio_input_turn_detection import ServerVad

async def livekit_cloud_token(agent_code: str, room_name: str) -> str:
    """A one-hour token that can only start this agent's avatar in this room.

    Never pass your API secret to the plugin: it copies `api_secret` into the avatar
    participant's attributes, which every participant in the room can read. The secret
    stays in this process and is only sent to bitHuman, to mint this token.
    """
    async with aiohttp.ClientSession() as http:
        async with http.post(
            "https://api.bithuman.ai/v1/runtime-tokens/mint",
            headers={"api-secret": os.environ["BITHUMAN_API_SECRET"]},
            json={"agent_code": agent_code, "scope": "livekit-cloud",
                  "room_name": room_name, "livekit_url": os.environ["LIVEKIT_URL"]},
        ) as resp:
            resp.raise_for_status()
            return (await resp.json())["scoped_token"]


async def entrypoint(ctx: JobContext):
    await ctx.connect()
    await ctx.wait_for_participant()

    # Create a cloud-hosted avatar session -- no local model needed
    avatar = bithuman.AvatarSession(
        avatar_id=os.environ["BITHUMAN_AGENT_ID"],
        api_secret=await livekit_cloud_token(os.environ["BITHUMAN_AGENT_ID"], ctx.room.name),
    )

    session = AgentSession(
        llm=openai.realtime.RealtimeModel(
            voice="coral",
            model="gpt-realtime-2.1-mini",
            # reply 0.5 s after you stop (the plugin's default semantic VAD can wait ~4 s)
            turn_detection=ServerVad(type="server_vad", silence_duration_ms=500, create_response=True, interrupt_response=True),
        ),
        vad=silero.VAD.load(),
    )

    await avatar.start(session, room=ctx.room)
    await session.start(
        agent=Agent(instructions="You are a helpful assistant. Keep answers short."),
        room=ctx.room,
        room_output_options=RoomOutputOptions(audio_enabled=False),
    )


if __name__ == "__main__":
    cli.run_app(WorkerOptions(entrypoint_fnc=entrypoint, worker_type=WorkerType.ROOM))
