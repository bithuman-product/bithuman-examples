# hello-voice-chat — the smallest `bitHumanKit` program

Twenty lines: a voice agent with no window, no avatar and no key. Speech
recognition, the language model and speech synthesis all run on the device.

## Run it

```bash
swift run -c release HelloVoiceChat
```

Speak into the microphone; Ctrl-C quits. The first launch downloads the weights
(about 3 GB, into `~/.cache/huggingface/hub/`); later launches start straight
away.

Override any field on `VoiceChatConfig` — the language, the voice, the system
prompt — before you hand it to `VoiceChat`. For the same agent in a window, see
[`macos-voice`](../macos-voice).

## Requirements

- An Apple Silicon Mac, M3 or newer, on macOS 26 or newer.
- Xcode 26 or newer, a microphone, and about 3 GB of disk.

No account, no key, no credits: the voice-only path is unmetered.
