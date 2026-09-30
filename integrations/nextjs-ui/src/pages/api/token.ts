import { NextApiRequest, NextApiResponse } from "next";
import { AccessToken, VideoGrant } from "livekit-server-sdk";

// DEMO CODE: this route is unauthenticated. Anyone who can reach it gets a
// one-hour LiveKit token for the room they name, so add your own login (or
// restrict the room names) before you deploy this app anywhere public.
//
// LiveKit auto-dispatches ROOM-type agent workers when a participant joins, so
// no explicit createDispatch is needed: issue a token and let the browser join.

const apiKey = process.env.LIVEKIT_API_KEY;
const apiSecret = process.env.LIVEKIT_API_SECRET;

// The values env.template ships with. Refuse them up front, with a message the
// page can show, instead of letting the browser hang on "Connecting...".
const PLACEHOLDERS = ["your-api-key", "your-api-secret", "your-livekit-server.com"];

function configProblem(clientUrl: string | undefined): string | null {
  if (!apiKey || !apiSecret) {
    return "LIVEKIT_API_KEY and LIVEKIT_API_SECRET are not set. Copy env.template to .env and fill in your LiveKit server's values, then restart the app.";
  }
  const values = [apiKey, apiSecret, clientUrl ?? ""];
  if (values.some((v) => PLACEHOLDERS.some((p) => v.includes(p)))) {
    return "The .env file still has the placeholder values from env.template. Set NEXT_PUBLIC_LIVEKIT_URL, LIVEKIT_API_KEY and LIVEKIT_API_SECRET to your LiveKit server's values, then restart the app.";
  }
  return null;
}

const ROOM_NAME = /^[A-Za-z0-9_-]{1,64}$/;

export default async function handleToken(
  req: NextApiRequest,
  res: NextApiResponse
) {
  try {
    // Client LiveKit URL. Under server.js (the docker-compose stacks) /rtc is
    // proxied to LiveKit, so the browser can use the same host:port as this app.
    const configuredUrl = process.env.NEXT_PUBLIC_LIVEKIT_URL;
    const problem = configProblem(configuredUrl);
    if (problem) {
      res.status(500).json({ error: problem });
      return;
    }

    const roomName = (req.query.roomName as string) || "default-room";
    const identity = (req.query.participantName as string) || `user-${Math.random().toString(36).substring(7)}`;
    if (!ROOM_NAME.test(roomName) || !ROOM_NAME.test(identity)) {
      res.status(400).json({ error: "roomName and participantName may use letters, digits, - and _ (64 at most)." });
      return;
    }

    const grant: VideoGrant = {
      room: roomName,
      roomJoin: true,
      roomCreate: true,
      canPublish: true,
      canPublishData: true,
      canSubscribe: true,
    };

    const at = new AccessToken(apiKey, apiSecret, {
      identity,
      name: identity,
      ttl: 3600,
    });

    at.addGrant(grant);
    const token = await at.toJwt();

    const clientUrl = configuredUrl || `ws://${req.headers.host || "localhost:3000"}`;

    res.status(200).json({
      accessToken: token,
      url: clientUrl,
      roomName,
      avatarImage: process.env.BITHUMAN_AVATAR_IMAGE || "",
    });
  } catch (e) {
    console.error("[token-api] Error:", e);
    res.status(500).json({ error: `Could not create a LiveKit token: ${(e as Error).message}` });
  }
}
