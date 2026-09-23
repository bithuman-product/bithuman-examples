# macos-voice — a voice agent on your Mac

A SwiftUI app that listens, thinks and answers out loud, with every step on the
device: speech recognition, the language model and speech synthesis. No avatar,
no account, no key, no credits.

## Run it

```bash
swift run MacOSVoice
```

Or open this directory in Xcode (*File → Open*, select the folder holding
`Package.swift`) and press Run. Grant the microphone when macOS asks.

The first launch downloads the language-model and speech weights into
`~/.cache/huggingface/hub/` — about 3 GB. Later launches start straight away,
and nothing goes over the network once the weights are there.

## What it does

`VoiceChatConfig` sets the language, the system prompt and the voice;
`VoiceChat` starts a session on the microphone. Those two types are the whole
API this example uses — override any field on the config before you pass it in.

For the same thing with no window at all, see
[`hello-voice-chat`](../hello-voice-chat). For an avatar on a Mac, see
[`macos-expression2`](../macos-expression2).

## Requirements

- An Apple Silicon Mac, M3 or newer, on macOS 26 or newer.
- Xcode 26 or newer.
- About 3 GB of disk for the weights, and a microphone.

## Documentation

- [Apple SDK](https://docs.bithuman.ai/sdk/apple)
- [Apple API reference](https://docs.bithuman.ai/sdk/apple-api)
