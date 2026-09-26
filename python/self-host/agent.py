"""Talk to a bitHuman avatar through your own LiveKit server.

OpenAI Realtime listens, thinks and speaks; the avatar is rendered HERE, inside
this process, on the CPU. Setup is in README.md. Run:  python agent.py dev
"""
import http.server, json, os, pathlib, secrets, sys, threading, urllib.parse, urllib.request, warnings
from datetime import timedelta

if not (3, 11) <= sys.version_info[:2] <= (3, 13):  # livekit-plugins-bithuman skips bithuman elsewhere
    sys.exit("This example needs Python 3.11, 3.12 or 3.13 (you have %d.%d)." % sys.version_info[:2])

from dotenv import load_dotenv
from livekit import api
from livekit.agents import Agent, AgentServer, AgentSession, AutoSubscribe, JobContext, cli
from livekit.agents.voice.room_io import RoomOptions
from livekit.plugins import bithuman, openai
from openai.types.realtime.realtime_audio_input_turn_detection import ServerVad

load_dotenv()
API = "https://api.bithuman.ai"
# ★ LOAD = THIS WORKER'S OWN SESSIONS, NOT THE WHOLE MACHINE'S CPU. The default
# load is host CPU, and livekit-server stops handing a worker rooms once its load
# passes 0.7 ("no servers available (received 1 responses)"): the avatar renders
# on this machine's CPU, so a busy machine left the page with no agent at all.
server = AgentServer(load_fnc=lambda s: min(len(s.active_jobs) / 4, 1.0))


def avatar_file(name: str) -> str:
    """A showcase slug, your agent code, or a file path -> a local avatar file (downloaded once)."""
    if pathlib.Path(name).is_file():
        return name
    dest = pathlib.Path.home() / ".cache" / "bithuman" / "examples" / f"{name}.imx"
    if not dest.is_file():
        showcase = json.load(urllib.request.urlopen(f"{API}/v1/models/showcase", timeout=30))["models"]
        url = next((m["url"] for m in showcase if name in (m["slug"], m["agent_code"])),
                   f"{API}/v1/agent/{name}/model/download")  # your own agent: needs your API secret
        ask = urllib.request.Request(url + ("&" if "?" in url else "?") + "redirect=false",
                                     headers={"api-secret": os.environ.get("BITHUMAN_MASTER_SECRET", "")})
        signed = json.load(urllib.request.urlopen(ask, timeout=30))["data"]["url"]
        print(f"Downloading avatar {name} (first run only) ...", flush=True)
        dest.parent.mkdir(parents=True, exist_ok=True)
        urllib.request.urlretrieve(signed, f"{dest}.part")
        os.replace(f"{dest}.part", dest)
    return str(dest)


@server.rtc_session()
async def entrypoint(ctx: JobContext):
    await ctx.connect(auto_subscribe=AutoSubscribe.AUDIO_ONLY)  # the agent listens; it never needs your camera
    session = AgentSession(llm=openai.realtime.RealtimeModel(
        model=os.getenv("BITHUMAN_REALTIME_MODEL", "gpt-realtime-2.1-mini"),
        voice=os.getenv("BITHUMAN_VOICE", "coral"),
        # reply 0.5 s after you stop (the plugin's default semantic VAD can wait ~4 s)
        turn_detection=ServerVad(type="server_vad", silence_duration_ms=500, create_response=True,
                                 interrupt_response=True)))
    # Local mode: the avatar renders in this process and publishes the lip-synced video AND audio.
    avatar = bithuman.AvatarSession(model_path=os.environ["BITHUMAN_MODEL_PATH"],
                                    api_secret=os.environ["BITHUMAN_MASTER_SECRET"])
    await avatar.start(session, room=ctx.room)
    await session.start(
        agent=Agent(instructions=os.getenv("BITHUMAN_INSTRUCTIONS", "You are a friendly assistant. Keep answers short.")),
        room=ctx.room, room_options=RoomOptions(audio_output=False, close_on_disconnect=False))


if __name__ == "__main__":
    # Your API secret is BITHUMAN_MASTER_SECRET here, passed to the plugin explicitly. Never
    # BITHUMAN_API_SECRET in a LiveKit worker: livekit-plugins-bithuman (1.8.4 and older) reads it by
    # itself and, for a cloud avatar, copies it into participant attributes everyone in the room can read.
    if os.getenv("BITHUMAN_API_SECRET"):
        sys.exit("Rename BITHUMAN_API_SECRET to BITHUMAN_MASTER_SECRET in .env (a LiveKit worker never gets BITHUMAN_API_SECRET).")
    for key in ("BITHUMAN_MASTER_SECRET", "OPENAI_API_KEY", "LIVEKIT_URL", "LIVEKIT_API_KEY", "LIVEKIT_API_SECRET"):
        if not os.getenv(key):
            sys.exit(f"{key} is not set. Copy .env.example to .env and fill it in.")
    # Resolved once, here: the job processes inherit it (the plugin also reads this variable).
    os.environ["BITHUMAN_MODEL_PATH"] = avatar_file(os.getenv("BITHUMAN_AVATAR", "wise-pup"))
    url = os.environ["LIVEKIT_URL"]
    warnings.filterwarnings("ignore", module="jwt")  # the dev key "secret" is short on purpose
    if urllib.parse.urlparse(url).hostname in ("localhost", "127.0.0.1", "::1"):  # your own machine only
        room = "bithuman-" + secrets.token_hex(3)  # a fresh room each run; the worker joins every new room
        token = (api.AccessToken().with_identity("you").with_ttl(timedelta(hours=24))
                 .with_grants(api.VideoGrants(room_join=True, room=room)).to_jwt())
        page = pathlib.Path(__file__).with_name("viewer.html").read_bytes()

        class Viewer(http.server.BaseHTTPRequestHandler):  # serves viewer.html, nothing else
            def do_GET(self):
                self.send_response(200); self.send_header("content-type", "text/html"); self.end_headers()
                self.wfile.write(page)

            def log_message(self, *args):
                pass

        viewer = http.server.ThreadingHTTPServer(("127.0.0.1", 8089), Viewer)
        threading.Thread(target=viewer.serve_forever, daemon=True).start()
        print("\nOpen in Chrome: http://localhost:8089/?"
              + urllib.parse.urlencode({"liveKitUrl": url, "token": token}) + "\n", flush=True)
    cli.run_app(server)
