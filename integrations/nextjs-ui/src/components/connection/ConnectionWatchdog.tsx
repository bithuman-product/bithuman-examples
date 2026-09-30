import React, { useEffect } from "react";
import { ConnectionState } from "livekit-client";
import {
  useConnectionState,
  useRemoteParticipants,
  useVoiceAssistant,
} from "@livekit/components-react";

// How long to wait before telling the user what is missing, instead of
// showing "Connecting..." forever.
const SERVER_TIMEOUT_MS = 15_000; // the browser cannot reach the LiveKit server
const AGENT_TIMEOUT_MS = 30_000; // connected, but no agent joined the room
const VIDEO_TIMEOUT_MS = 45_000; // an agent joined, but no avatar video arrived

/**
 * Watches the room and reports, in plain words, which piece is missing:
 * the LiveKit server, the Python agent, or the avatar video.
 */
export function ConnectionWatchdog({
  serverUrl,
  roomName,
  onProblem,
}: {
  serverUrl: string;
  roomName: string;
  onProblem: (message: string) => void;
}) {
  const state = useConnectionState();
  const remotes = useRemoteParticipants();
  const { videoTrack } = useVoiceAssistant();
  const agentJoined = remotes.length > 0;
  const hasVideo = Boolean(videoTrack);

  useEffect(() => {
    if (state === ConnectionState.Connected) return;
    const t = setTimeout(
      () =>
        onProblem(
          `Could not reach the LiveKit server at ${serverUrl} within ${SERVER_TIMEOUT_MS / 1000} s. ` +
            "Check NEXT_PUBLIC_LIVEKIT_URL in .env and that the server is running " +
            "(for a local server: livekit-server --dev, then ws://localhost:7880)."
        ),
      SERVER_TIMEOUT_MS
    );
    return () => clearTimeout(t);
  }, [state, serverUrl, onProblem]);

  useEffect(() => {
    if (state !== ConnectionState.Connected || agentJoined) return;
    const t = setTimeout(
      () =>
        onProblem(
          `Connected to LiveKit, but no agent joined room "${roomName}" within ${AGENT_TIMEOUT_MS / 1000} s. ` +
            "This app is only the front end: start a bitHuman LiveKit agent against the same LiveKit server " +
            "(for example python/cloud-essence/agent.py dev or python/self-host/agent.py dev) and reload."
        ),
      AGENT_TIMEOUT_MS
    );
    return () => clearTimeout(t);
  }, [state, agentJoined, roomName, onProblem]);

  useEffect(() => {
    if (state !== ConnectionState.Connected || !agentJoined || hasVideo) return;
    const t = setTimeout(
      () =>
        onProblem(
          `An agent joined room "${roomName}", but no avatar video arrived within ${VIDEO_TIMEOUT_MS / 1000} s. ` +
            "Check the agent's terminal for a bitHuman error (API secret, agent code, or avatar file)."
        ),
      VIDEO_TIMEOUT_MS
    );
    return () => clearTimeout(t);
  }, [state, agentJoined, hasVideo, roomName, onProblem]);

  return null;
}

/** Full-screen message with a retry button; replaces the endless spinner. */
export function ConnectionProblem({ message }: { message: string }) {
  return (
    <div
      role="alert"
      data-connection-problem
      className="fixed inset-0 z-[100] flex items-center justify-center bg-black/90 p-6 text-white"
    >
      <div className="max-w-xl rounded-xl border border-red-300/30 bg-red-500/10 p-6">
        <h2 className="mb-3 text-lg font-semibold">The avatar could not start</h2>
        <p className="mb-5 text-sm leading-relaxed text-red-100">{message}</p>
        <p className="mb-5 text-xs text-gray-400">
          Setup: README.md in integrations/nextjs-ui (a LiveKit server and a running Python agent are required).
        </p>
        <button
          className="rounded-lg bg-white/10 px-4 py-2 text-sm hover:bg-white/20"
          onClick={() => window.location.reload()}
        >
          Retry
        </button>
      </div>
    </div>
  );
}
