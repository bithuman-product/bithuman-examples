# macos-expression2 — an Expression 2 avatar on your Mac

A small command-line tool: a 16 kHz WAV goes in, lip-synced frames come out,
rendered on this machine. It needs your API secret
(`export BITHUMAN_API_SECRET=…`; create one at
[bithuman.ai/developer/api-keys](https://www.bithuman.ai/developer/api-keys), Creator plan
or higher from 12 October 2026): the engine checks it when the session starts and bills
active session time ([pricing](https://docs.bithuman.ai/pricing)).

This is the shortest native Apple path there is. The same `Expression2` product
and the same three calls — `create`, `feed`, `pull` — also run on an iPhone; see
[`ios-expression2`](../ios-expression2) for the app shape.

## Run it

```bash
./setup.sh                              # ~365 MB, anonymous
swift run -c release MacOSExpression2
```

`setup.sh` puts three files in `Model/`:

| file | what it is |
|---|---|
| `agent.imx` | the identity. `./setup.sh <YOUR_AGENT_CODE>` with `BITHUMAN_API_SECRET` set fetches yours instead |
| `shared-engine.imx` | the engine graphs every identity shares — one per platform, not one per identity |
| `speech16k.wav` | 16 kHz mono speech out of the identity's own bundle |

None of them is committed.

## Measured

Re-checked 2026-09-30 on an Apple M4 (macOS 26.6.2, Xcode 26.3, Swift package
2.19.3): 407 frames for 20.34 s, `out/first-frame.png` 416x720.

On a MacBook Pro (Apple M4 Max, macOS 26.5, Xcode 26.5, Swift 6.3.2) on
2026-09-22, against the public showcase identity `A23WJF0199`, with the machine
busy with other work:

```
engine ready: 416x720, isReady=true
audio: 325451 samples, 20.34 s
generated 407 frames in 13.02 s (31.3 FPS, 1.56x real time) -> out/first-frame.png
```

`out/first-frame.png` reads 416x720, min 0, max 255, mean 102.91 — a picture,
not an empty buffer. Most of the first run is the engine compiling its graphs
for this machine; keep `Model/staged/` and the next start is much faster.

## Requirements

- An Apple Silicon Mac, **macOS 14 or newer**, and Xcode 26 or newer. `Package.swift`
  targets macOS 14: the Mac engine core the `Expression2` product links is built for
  macOS 14 (a macOS 13 target links with a "built for newer 'macOS' version (14.0)"
  warning and is not verified to run on 13).
- About 800 MB of disk: 365 MB of downloads and the directory the engine
  unpacks them into.

## What the build and the run print

With Swift package 2.19.3 and Xcode 26.3 the release build prints no warnings
(checked 2026-09-30). The run also prints the engine's own `[embody…]` log lines
between the three lines above; they are informational.

Without an API secret the tool stops before it renders: it prints `error:` followed
by the engine's reason (which names `BITHUMAN_API_SECRET` and where to get a key) and
exits with code 1, rather than crashing.
