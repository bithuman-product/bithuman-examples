# Integrations

Framework and language bridges that show how to connect bitHuman to different stacks. Each integration demonstrates a specific runtime, language, or deployment pattern -- pick the one closest to what you are building.

## Examples

| Example | Stack | Description | When to use |
|---------|-------|-------------|-------------|
| [nextjs-ui/](nextjs-ui/) | Next.js 14, TypeScript, Tailwind, LiveKit | A web front end for LiveKit avatar sessions: the avatar's video, microphone and camera controls, and a voice-activity indicator. | You want a browser front end for your LiveKit avatar agent to start from. |
| [java-websocket/](java-websocket/) | Java 17, Maven, WebSocket | Java client that streams PCM audio to a Python bitHuman server over WebSocket and receives JPEG video frames back. Includes the full wire protocol spec. | You are integrating bitHuman into a Java backend, Android app, or Spring service. |
| [gradio-web/](gradio-web/) | Python, Gradio, FastRTC | Browser UI powered by Gradio with FastRTC for WebRTC transport. Select an avatar from a dropdown, talk through your mic, see the avatar respond. | You want a quick browser demo without LiveKit or Node.js -- pure Python. |
| [offline-mac/](offline-mac/) | macOS, Docker, Ollama, Apple Speech | An avatar agent whose conversation runs on your Mac: Ollama for the language model, Apple Speech Recognition for STT, Apple Voices for TTS, and the bitHuman SDK for the avatar. The avatar checks your API secret online when a session starts. | You want the conversation (speech, language model, voice) on your own machine. For no internet at all, see [Fully offline](https://docs.bithuman.ai/deploy/offline): Business and Enterprise, Linux PCs and terminals. |

## Prerequisites

Each integration has its own prerequisites listed in its README. Common requirements:

- A bitHuman API secret -- get one at [www.bithuman.ai](https://www.bithuman.ai/developer/api-keys) (Developer > API Secrets; Creator plan or higher from 12 October 2026)
- `.imx` model files for Essence-based integrations (download from [www.bithuman.ai](https://www.bithuman.ai))

## Getting started

```bash
git clone https://github.com/bithuman-product/bithuman-examples.git
cd bithuman-examples/integrations/<example>
```

Each subdirectory has its own README with setup steps.

## Documentation

- [Python SDK](https://docs.bithuman.ai/platforms/python)
- [Swift package (iOS & macOS)](https://docs.bithuman.ai/platforms/ios)
- [API overview](https://docs.bithuman.ai/api)
- [LiveKit integration](https://docs.bithuman.ai/platforms/livekit)
- [Python SDK on PyPI](https://pypi.org/project/bithuman/)
