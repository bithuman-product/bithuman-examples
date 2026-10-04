# nextjs-ui — a web front end for a LiveKit avatar agent

> **Before you start: this app is only a front end.** It shows nothing on its own.
> It needs **(1) a LiveKit server** and **(2) a running Python agent** (the part that
> talks and renders the bitHuman avatar), both pointed at the same LiveKit server.
> Want an avatar on a web page with no servers at all? Use the one-iframe embed
> instead: [Web](https://docs.bithuman.ai/platforms/web).

A Next.js app that joins a LiveKit room and shows your bitHuman avatar agent: the
avatar's video, your microphone and camera controls, and a voice-activity indicator.

![The nextjs-ui front end](./public/example-screenshot.jpg)

## What you need

| Piece | Where it comes from |
|---|---|
| Node.js 18.18 or newer, and npm | [nodejs.org](https://nodejs.org) |
| A LiveKit server, its URL, API key and API secret | [LiveKit Cloud](https://livekit.io/cloud), or your own: `livekit-server --dev` gives `ws://localhost:7880`, key `devkey`, secret `secret` |
| A running bitHuman LiveKit agent on that server | [`python/self-host/`](../../python/self-host/) (avatar rendered on your machine) or [`python/cloud-essence/`](../../python/cloud-essence/) (avatar rendered in the bitHuman cloud). They need a bitHuman API secret (Creator plan or higher from 12 October 2026) and an OpenAI key; this front end needs neither |

## Run it

```bash
# terminal 1: a LiveKit server (skip if you use LiveKit Cloud)
livekit-server --dev

# terminal 2: the agent, e.g. python/self-host (see its README for its .env)
cd bithuman-examples/python/self-host && python agent.py dev

# terminal 3: this app
cd bithuman-examples/integrations/nextjs-ui
npm install
cp env.template .env      # set NEXT_PUBLIC_LIVEKIT_URL, LIVEKIT_API_KEY, LIVEKIT_API_SECRET
npm run dev               # http://localhost:3000
```

For a local `livekit-server --dev`, `.env` is:

```env
NEXT_PUBLIC_LIVEKIT_URL=ws://localhost:7880
LIVEKIT_API_KEY=devkey
LIVEKIT_API_SECRET=secret
```

## If it does not connect

The page does not spin on "Connecting..." forever: it stops and says which piece is missing.

| The page says | What to do |
|---|---|
| `.env` still has the placeholder values, or `LIVEKIT_API_KEY ... not set` | Fill in `.env` from your LiveKit server, then restart `npm run dev` |
| Could not connect to / could not reach the LiveKit server at ... (within 15 s) | Check `NEXT_PUBLIC_LIVEKIT_URL` and that the server is running |
| Connected to LiveKit, but no agent joined the room (after 30 s) | Start your Python agent against the **same** LiveKit server, then select Retry |
| An agent joined, but no avatar video arrived (after 45 s) | Read the agent's terminal: usually the bitHuman API secret, the agent code or the avatar file |

## Configuration

`.env` (see `env.template`):

```env
# The LiveKit URL the browser connects to
NEXT_PUBLIC_LIVEKIT_URL=wss://your-livekit-server.com

# Used by /api/token to mint the browser's LiveKit access token
LIVEKIT_API_KEY=your-api-key
LIVEKIT_API_SECRET=your-api-secret

# Frontend settings (JSON)
NEXT_PUBLIC_APP_CONFIG={}

# Optional — read by server.js and /api/token when the app runs behind a docker-compose stack
LIVEKIT_WS_URL=http://livekit:17880     # internal LiveKit URL
PORT=3000                               # Next.js listen port
BITHUMAN_AVATAR_IMAGE=                  # avatar background image URL
```

The LiveKit API secret stays on the server: `/api/token` uses it to mint the browser's
access token, and the browser never sees it. No bitHuman credential belongs in
this app.

> **`/api/token` is unauthenticated demo code.** Anyone who can reach it gets a
> one-hour LiveKit token for a room, which in turn starts your agent (and its
> metered bitHuman session). Add your own login, or restrict room names, before
> you deploy this app anywhere public.

For `npm run dev` and `npm start`, `PORT`, `LIVEKIT_WS_URL` and `BITHUMAN_AVATAR_IMAGE`
default to `3000`, the LiveKit container's internal URL, and empty.

## Project structure

```
src/
  components/
    playground/     the video and controls
    connection/     connection management and the watchdog that explains a failed connection
    toast/          notifications
  contexts/         React contexts
  hooks/            React hooks
  pages/
    api/token.ts    mints the LiveKit access token
    index.tsx       the main page
    [agentCode].tsx a page per agent code
  styles/           global styles
public/             static assets
server.js           the server used by the docker-compose stacks
```

Built with Next.js 15 (Pages Router), React 18, TypeScript, Tailwind CSS, Framer Motion
and `livekit-client`.

## Deploy

It is a standard Next.js app: deploy it to Vercel, Netlify or any Node.js host, and set
the environment variables above there. The docker-compose stacks in
`python/cloud-essence/` and `integrations/offline-mac/` build it through their own
`webui.dockerfile`; there is no standalone Dockerfile in this directory.

## License

Apache 2.0 — see [LICENSE](LICENSE). Contributions: [CONTRIBUTING.md](CONTRIBUTING.md).
Issues: [bithuman-examples/issues](https://gitlab.com/bithuman/sdk/bithuman-examples/-/issues).
