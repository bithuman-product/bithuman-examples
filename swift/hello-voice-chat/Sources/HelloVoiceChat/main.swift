// The smallest bitHumanKit program: a voice agent with no window and no key.
// Run with:  swift run -c release HelloVoiceChat
import bitHumanKit
import Foundation

@main
struct HelloVoiceChat {
    static func main() async throws {
        // Default config: bundled cloned voice, en-US, built-in
        // friendly-assistant prompt. Override any field on
        // `VoiceChatConfig` before passing it in.
        var config = VoiceChatConfig()
        config.systemPrompt = "You are a deadpan ship's computer. One-sentence answers."

        let chat = await MainActor.run { VoiceChat(config: config) }
        try await chat.start()

        // Park forever; Ctrl-C tears the process down.
        let forever = AsyncStream<Void> { _ in }
        for await _ in forever { break }
        _ = chat
    }
}
