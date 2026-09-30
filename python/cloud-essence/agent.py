"""bitHuman Essence avatar agent -- cloud-hosted (no local models needed).

Usage:
    python agent.py dev        # local dev with LiveKit playground
    python agent.py start      # production worker
"""

import logging
import os
import sys

import aiohttp
from dotenv import load_dotenv
from livekit.agents import (
    Agent,
    AgentSession,
    JobContext,
    RoomOutputOptions,
    WorkerOptions,
    WorkerType,
    cli,
)
from livekit.plugins import bithuman, openai, silero
from openai.types.realtime.realtime_audio_input_turn_detection import ServerVad

logger = logging.getLogger("bithuman-agent")
logger.setLevel(logging.INFO)

# Only this folder's .env: a bare load_dotenv() also searches every parent folder.
load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env"))


def check_secret_env() -> None:
    """A LiveKit worker keeps your API secret as BITHUMAN_MASTER_SECRET and uses it only to mint.

    Never BITHUMAN_API_SECRET: livekit-plugins-bithuman (1.8.4 and older) reads that
    name by itself whenever `api_secret=` is omitted and copies it into the avatar's
    participant attributes, which everyone in the room can read.
    """
    if os.getenv("BITHUMAN_API_SECRET"):
        sys.exit("Rename BITHUMAN_API_SECRET to BITHUMAN_MASTER_SECRET (in .env or your shell). "
                 "The LiveKit plugin copies BITHUMAN_API_SECRET into the room, where everyone can read it.")
    if not os.getenv("BITHUMAN_MASTER_SECRET"):
        sys.exit("Set BITHUMAN_MASTER_SECRET (your API secret) in .env.")


async def livekit_cloud_token(agent_code: str, room_name: str) -> str:
    """A one-hour token that can only start this agent's avatar in this room.

    Why: for a cloud avatar, the plugin copies whatever it gets as `api_secret` into the
    avatar participant's attributes, which every participant in the room can read. So
    the plugin gets this short-lived, single-room token, and your real secret stays in
    this process; it is only ever sent to api.bithuman.ai, to mint the token.
    """
    async with aiohttp.ClientSession() as http:
        async with http.post(
            "https://api.bithuman.ai/v1/runtime-tokens/mint",
            headers={"api-secret": os.environ["BITHUMAN_MASTER_SECRET"]},
            json={"agent_code": agent_code, "scope": "livekit-cloud",
                  "room_name": room_name, "livekit_url": os.environ["LIVEKIT_URL"]},
        ) as resp:
            if resp.status != 200:
                # The body names the problem (a mistyped secret, an unknown agent code, ...).
                raise RuntimeError(f"bitHuman refused to mint a room token ({resp.status}): "
                                   f"{(await resp.text())[:300]}")
            return (await resp.json())["scoped_token"]


def agent_code() -> str:
    """Your agent code, e.g. A23WJF0199 (BITHUMAN_AGENT_ID; BITHUMAN_AGENT_CODE also works)."""
    code = os.getenv("BITHUMAN_AGENT_ID") or os.getenv("BITHUMAN_AGENT_CODE")
    if not code:
        sys.exit("Set BITHUMAN_AGENT_ID to your agent code (the public sample is A23WJF0199; "
                 "yours are on www.bithuman.ai).")
    return code


async def entrypoint(ctx: JobContext):
    await ctx.connect()
    await ctx.wait_for_participant()

    avatar_id = agent_code()
    logger.info(f"Cloud avatar -- agent code: {avatar_id}")

    avatar = bithuman.AvatarSession(
        avatar_id=avatar_id,
        # The plugin's parameter is named api_secret, but it receives the minted
        # room token here, never your API secret (cloud mode takes no api_token=).
        api_secret=await livekit_cloud_token(avatar_id, ctx.room.name),
    )

    session = AgentSession(
        llm=openai.realtime.RealtimeModel(
            voice=os.getenv("OPENAI_VOICE", "coral"),
            model="gpt-realtime-2.1-mini",
            # reply 0.5 s after you stop (the plugin's default semantic VAD can wait ~4 s)
            turn_detection=ServerVad(type="server_vad", silence_duration_ms=500, create_response=True, interrupt_response=True),
        ),
        vad=silero.VAD.load(),
    )

    await avatar.start(session, room=ctx.room)

    await session.start(
        agent=Agent(
            instructions=os.getenv("AGENT_PROMPT", "You are a helpful assistant. Respond concisely.")
        ),
        room=ctx.room,
        room_output_options=RoomOutputOptions(audio_enabled=False),
    )


if __name__ == "__main__":
    check_secret_env()
    agent_code()
    cli.run_app(
        WorkerOptions(
            entrypoint_fnc=entrypoint,
            worker_type=WorkerType.ROOM,
            job_memory_warn_mb=1500,
            num_idle_processes=1,
        )
    )
