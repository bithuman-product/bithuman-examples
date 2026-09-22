# macos-expression2 — an Expression 2 avatar on your Mac

A small command-line tool: a 16 kHz WAV goes in, lip-synced frames come out,
all on this machine. No server, no account, no key, no credits.

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

On a MacBook Pro (Apple M4 Max, macOS 26.5, Xcode 26.5, Swift 6.3.2) on
2026-09-22, against the free showcase identity `A23WJF0199`, with the machine
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

- An Apple Silicon Mac, macOS 13 or newer, and Xcode 26 or newer.
- About 800 MB of disk: 365 MB of downloads and the directory the engine
  unpacks them into.

## What the build prints

The shipped `Expression2` framework carries debug paths from the machine that
built it, so every link emits ten warnings naming a directory that does not
exist on your Mac:

```text
warning: (arm64) /Users/…/Build/Intermediates.noindex/… unable to open object
file: No such file or directory
```

They are harmless — the build completes and the binary runs — and there is
nothing to do about them on this side.
