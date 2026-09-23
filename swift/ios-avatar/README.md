# ios-avatar — the `bitHumanKit` voice agent on iPhone and iPad

A whole conversation on the device — speech recognition, a language model,
speech synthesis and a lip-synced avatar — from one product, `bitHumanKit`.

**This directory is source to read and copy, not a project to run.** It is a
SwiftPM package, and a SwiftPM `.executableTarget` builds no `.app`: there is no
scheme to run on a phone and no *Signing & Capabilities* tab. To put this on a
device, make an app project of your own, add the package to it and paste
`Sources/IOSAvatarApp.swift` in. The whole path, step by step, is at
[docs.bithuman.ai/examples/swift-ios-voice-agent](https://docs.bithuman.ai/examples/swift-ios-voice-agent).

For an avatar you can build and run on a phone today, with no device floor and
no entitlement, take [`ios-expression2`](../ios-expression2) instead — it ships
a real Xcode project.

## Before you clone this

This is the most demanding Apple path bitHuman has. In order, because Apple's
reply is the long pole:

1. **Request two Apple entitlements.** developer.apple.com → Account →
   Membership → *Request Additional Capabilities*:

   ```text
   com.apple.developer.kernel.increased-memory-limit
   com.apple.developer.kernel.extended-virtual-addressing
   ```

   Apple has taken **1–3 business days**. Without them iOS terminates the app
   about half a minute into a live turn, when it passes the ~3 GB default
   ceiling, with no crash you can read. They are **entitlements**: they are
   signed in from the file `CODE_SIGN_ENTITLEMENTS` names. Copying them into an
   `Info.plist` — including the one in this directory — grants nothing.
2. **Check the device.** iPhone 16 Pro or later, or iPad Pro M4 or later
   (16 GB), on iOS or iPadOS 26 or newer. `HardwareCheck.evaluate()` refuses
   anything else at launch: iPhone 15 Pro and earlier, iPhone 16 and 16 Plus,
   iPad Air M2 and M3, iPad Pro M1 and M2. The Simulator cannot stand in.
3. **Get an API secret** — free at
   [Developer → API Secrets](https://www.bithuman.ai/developer/api-keys). Set
   `BITHUMAN_API_SECRET` in your scheme under *Product → Scheme → Edit Scheme →
   Run → Arguments → Environment Variables*, never in source. The app reads it
   and hands it to `bitHumanKit` as `config.apiKey` (a field that keeps its
   published name).
   Avatar mode is metered; the voice-only path is not.
4. **Leave room.** The first launch downloads about 1.6 GB of weights.

## Files

| File | Purpose |
|---|---|
| `Package.swift` | the manifest — `bitHumanKit` from the published tap |
| `Sources/IOSAvatarApp.swift` | the whole app: the hardware gate, the avatar lifecycle, a `UIViewRepresentable` host and the views |
| `Sources/Info.plist` | the privacy strings and entitlement keys to copy into **your** app target |

## Documentation

- [Swift / iOS — Hello, avatar](https://docs.bithuman.ai/examples/swift-ios-voice-agent) — the whole path, every file
- [Apple SDK](https://docs.bithuman.ai/sdk/apple) · [Apple API reference](https://docs.bithuman.ai/sdk/apple-api)
