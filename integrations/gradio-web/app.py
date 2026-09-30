"""Web-based bitHuman avatar with Gradio + FastRTC.

Opens a browser UI where you can talk to an AI agent through a bitHuman avatar
rendered on this machine. Every .imx file in BITHUMAN_MODEL_ROOT is offered in a
dropdown. Your bitHuman API secret stays on the server; the page never sees it.

Usage:
    python app.py        # http://localhost:7860
"""

import asyncio
import json
import logging
import os
import sys
import time
import urllib.request
from collections.abc import AsyncIterator
from pathlib import Path

import gradio as gr
import numpy as np
from dotenv import load_dotenv
from livekit import rtc
from livekit.agents import utils
from livekit.agents.voice import Agent, AgentSession
from livekit.agents.voice.avatar import AudioSegmentEnd, QueueAudioOutput
from livekit.plugins import openai
from numpy.typing import NDArray
from openai.types.realtime.realtime_audio_input_turn_detection import ServerVad

from bithuman import AsyncBithuman
from fastrtc import AsyncAudioVideoStreamHandler, AudioEmitType, Stream, VideoEmitType, wait_for_item


# --- Inline replacement for bithuman.utils.FPSController (removed in SDK 2.3). ---
# Tiny time.monotonic() pacer. Surface matches the original:
#   wait_next_frame(sleep=False) -> float seconds until next frame deadline
#   update()                     -> record that a frame was emitted
#   average_fps                  -> float, recent observed FPS
class FPSController:
    def __init__(self, target_fps: int = 25, window: int = 50):
        self._target_dt = 1.0 / float(target_fps)
        self._next_t = time.monotonic()
        self._window = window
        self._ticks: list[float] = []

    def wait_next_frame(self, sleep: bool = True) -> float:
        now = time.monotonic()
        wait = self._next_t - now
        if wait > 0 and sleep:
            time.sleep(wait)
        return max(wait, 0.0)

    def update(self) -> None:
        now = time.monotonic()
        self._next_t += self._target_dt
        # If we've fallen badly behind (e.g. a long pause), resync.
        if self._next_t < now - self._target_dt:
            self._next_t = now + self._target_dt
        self._ticks.append(now)
        if len(self._ticks) > self._window:
            self._ticks.pop(0)

    @property
    def average_fps(self) -> float:
        if len(self._ticks) < 2:
            return 0.0
        span = self._ticks[-1] - self._ticks[0]
        return (len(self._ticks) - 1) / span if span > 0 else 0.0
# --- end inline FPSController ---

# Only this folder's .env: a bare load_dotenv() also searches every parent folder.
load_dotenv(Path(__file__).with_name(".env"))
logger = logging.getLogger("bithuman-web")
logging.basicConfig(level=logging.INFO)

API = "https://api.bithuman.ai"
SAMPLE = "wise-pup"  # a public showcase avatar (Expression 2), downloaded when the folder has none

# Server-side only. The secret is read here, in this process, and never put into
# the page: Gradio sends every component's value to the browser, so a textbox
# pre-filled with it would hand it to anyone who opens the page.
API_SECRET = os.getenv("BITHUMAN_API_SECRET")
if not API_SECRET:
    sys.exit("Set BITHUMAN_API_SECRET in .env (www.bithuman.ai -> Developer -> API Secrets).")
if not os.getenv("OPENAI_API_KEY"):
    sys.exit("Set OPENAI_API_KEY in .env (OpenAI Realtime does the listening and speaking).")

MODEL_ROOT = Path(os.getenv("BITHUMAN_MODEL_ROOT") or Path.home() / ".cache" / "bithuman" / "examples")


def download_sample(name: str) -> None:
    """Fetch a public showcase avatar into MODEL_ROOT (first run only)."""
    showcase = json.load(urllib.request.urlopen(f"{API}/v1/models/showcase", timeout=30))["models"]
    url = next(m["url"] for m in showcase if m["slug"] == name)
    ask = urllib.request.Request(url + ("&" if "?" in url else "?") + "redirect=false")
    signed = json.load(urllib.request.urlopen(ask, timeout=30))["data"]["url"]
    dest = MODEL_ROOT / f"{name}.imx"
    print(f"No .imx files in {MODEL_ROOT}; downloading the sample avatar {name} once ...", flush=True)
    MODEL_ROOT.mkdir(parents=True, exist_ok=True)
    urllib.request.urlretrieve(signed, f"{dest}.part")
    os.replace(f"{dest}.part", dest)


if not any(MODEL_ROOT.glob("*.imx")):
    download_sample(SAMPLE)


class BitHumanHandler(AsyncAudioVideoStreamHandler):
    """Bridges FastRTC audio/video streams with a bitHuman avatar."""

    AVATARS = {
        p.stem: str(p.resolve())
        for p in sorted(MODEL_ROOT.glob("*.imx"))
    }

    def __init__(self):
        super().__init__(
            input_sample_rate=24_000, output_sample_rate=16_000,
            output_frame_size=320, fps=100,
        )
        # Plain queues only here. Anything from livekit-agents that needs an event
        # loop (QueueAudioOutput) is built in start_up(), which runs on the loop:
        # this constructor also runs at import time, where Python 3.14 has none.
        self.input_audio_queue: asyncio.Queue[rtc.AudioFrame] = asyncio.Queue()
        self.agent_audio_queue: QueueAudioOutput | None = None
        self.video_queue: asyncio.Queue[NDArray[np.uint8]] = asyncio.Queue()
        self.audio_queue: asyncio.Queue[tuple[int, NDArray[np.int16]]] = asyncio.Queue()
        self.runtime: AsyncBithuman | None = None
        self.runtime_ready = asyncio.Event()
        self.fps_controller: FPSController | None = None
        self.pushed_duration: float = 0

    @utils.log_exceptions(logger=logger)
    async def start_up(self):
        await self.wait_for_args()
        avatar_name = self.latest_args[1]

        self.agent_audio_queue = QueueAudioOutput(sample_rate=16_000)

        utils.http_context._new_session_ctx()
        session = AgentSession()
        session.input.audio = self._make_audio_input()
        session.output.audio = self.agent_audio_queue
        await session.start(agent=Agent(
            instructions="You are a friendly assistant.",
            llm=openai.realtime.RealtimeModel(
                voice="alloy",
                # reply 0.5 s after you stop (the plugin's default semantic VAD can wait ~4 s)
                turn_detection=ServerVad(type="server_vad", silence_duration_ms=500, create_response=True, interrupt_response=True),
            ),
        ))

        self.agent_audio_queue.on("clear_buffer", self._on_interrupt)

        self.runtime = await AsyncBithuman.create(
            api_secret=API_SECRET, model_path=self.AVATARS[avatar_name],
        )
        # Pace frames at the avatar's own rate (Essence 2: 25 fps, Expression 2: 20).
        self.fps_controller = FPSController(target_fps=round(self.runtime.fps or 25))
        self.runtime_ready.set()

        await asyncio.gather(self._generate_frames(), self._forward_agent_audio())

    def _make_audio_input(self) -> AsyncIterator[rtc.AudioFrame]:
        async def gen():
            while True:
                yield await self.input_audio_queue.get()
        return gen()

    async def _generate_frames(self):
        async for frame in self.runtime.run():
            if frame.audio_chunk:
                await self.audio_queue.put((frame.audio_chunk.sample_rate, frame.audio_chunk.data))
                self.pushed_duration += frame.audio_chunk.duration

            if frame.has_image:
                sleep = self.fps_controller.wait_next_frame(sleep=False)
                if sleep > 0:
                    await asyncio.sleep(sleep)
                await self.video_queue.put(frame.bgr_image)
                self.fps_controller.update()

            if frame.end_of_speech and self.pushed_duration > 0:
                self.agent_audio_queue.notify_playback_finished(self.pushed_duration, interrupted=False)
                self.pushed_duration = 0

    async def _forward_agent_audio(self):
        async for frame in self.agent_audio_queue:
            if isinstance(frame, AudioSegmentEnd):
                await self.runtime.flush()
            else:
                await self.runtime.push_audio(bytes(frame.data), frame.sample_rate, last_chunk=False)

    def _on_interrupt(self):
        self.runtime.interrupt()
        if self.pushed_duration > 0:
            self.agent_audio_queue.notify_playback_finished(self.pushed_duration, interrupted=True)
            self.pushed_duration = 0

    # FastRTC hooks
    async def video_emit(self) -> VideoEmitType:
        frame = await wait_for_item(self.video_queue)
        return frame if frame is not None else np.zeros((768, 1280, 3), dtype=np.uint8)

    async def video_receive(self, frame: NDArray[np.uint8]):
        pass

    async def emit(self) -> AudioEmitType:
        return await wait_for_item(self.audio_queue)

    async def receive(self, frame: tuple[int, NDArray[np.int16]]):
        await self.runtime_ready.wait()
        sr, array = frame
        if array.ndim == 2:
            array = array[0]
        if array.dtype == np.float32:
            array = (array * np.iinfo(np.int16).max).astype(np.int16)
        await self.input_audio_queue.put(
            rtc.AudioFrame(data=array.tobytes(), sample_rate=sr, num_channels=1, samples_per_channel=len(array))
        )

    async def shutdown(self):
        if self.runtime:
            await self.runtime.flush()
            await self.runtime.stop()

    def copy(self) -> "BitHumanHandler":
        return BitHumanHandler()


stream = Stream(
    handler=BitHumanHandler(),
    mode="send-receive",
    modality="audio-video",
    additional_inputs=[
        # The API secret is deliberately NOT an input: it stays in this process (API_SECRET).
        gr.Dropdown(choices=list(BitHumanHandler.AVATARS.keys()), value=next(iter(BitHumanHandler.AVATARS), None), label="Avatar"),
    ],
    ui_args={"title": "bitHuman Avatar"},
)

if __name__ == "__main__":
    # Local only by default. Anyone who can open this page can start metered
    # sessions on your API secret, so add your own login before exposing it
    # (for example with share=True or on a public host).
    stream.ui.launch(server_name=os.getenv("GRADIO_SERVER_NAME", "127.0.0.1"))
