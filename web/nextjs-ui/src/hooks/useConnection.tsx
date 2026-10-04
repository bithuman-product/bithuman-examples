"use client"

import React, { createContext, useContext, useState, useCallback } from 'react';
import { useConfig } from '@/hooks/useConfig';

export type ConnectionMode = "env" | "manual";

type TokenGeneratorData = {
  shouldConnect: boolean;
  wsUrl: string;
  token: string;
  mode: ConnectionMode;
  avatarImage: string;
  roomName: string;
  /** A problem the page should show instead of spinning on "Connecting..." */
  error: string | null;
  setError: (error: string | null) => void;
  disconnect: () => Promise<void>;
  connect: (mode: ConnectionMode) => Promise<void>;
};

const ConnectionContext = createContext<TokenGeneratorData | undefined>(undefined);

export const ConnectionProvider = ({
  children,
}: {
  children: React.ReactNode;
}) => {
  const { config } = useConfig();
  const [error, setError] = useState<string | null>(null);
  const [roomName, setRoomName] = useState("");
  const [connectionDetails, setConnectionDetails] = useState<{
    wsUrl: string;
    token: string;
    mode: ConnectionMode;
    shouldConnect: boolean;
    avatarImage: string;
  }>({ wsUrl: "", token: "", shouldConnect: false, mode: "manual", avatarImage: "" });

  const connect = useCallback(
    async (mode: ConnectionMode) => {
      // Prevent duplicate requests
      if (connectionDetails.shouldConnect && connectionDetails.mode === mode) {
        console.log('[connection] Already connected with the same mode, skipping duplicate request');
        return;
      }

      // Set connecting state immediately to prevent parallel requests
      setConnectionDetails(prev => ({ ...prev, mode }));

      let token = "";
      let url = "";
      let avatarImage = "";

      if (mode === "env") {
        // Simple parameter setup
        const params = new URLSearchParams();
        if (config.settings.room_name) {
          params.append('roomName', config.settings.room_name);
        }
        if (config.settings.participant_name) {
          params.append('participantName', config.settings.participant_name);
        }

        // Get token and LiveKit URL from the API.
        // The server auto-detects the correct URL from the request host,
        // so this works on localhost AND remote VPS with zero config.
        const tokenUrl = `/api/token?${params.toString()}`;
        try {
          const response = await fetch(tokenUrl);
          const data = await response.json().catch(() => ({}));
          if (!response.ok) {
            throw new Error(data.error || `/api/token answered ${response.status}. Check the terminal running this app.`);
          }
          token = data.accessToken;
          url = data.url || process.env.NEXT_PUBLIC_LIVEKIT_URL || '';
          avatarImage = data.avatarImage || '';
          setRoomName(data.roomName || config.settings.room_name || '');
          if (!token || !url) {
            throw new Error("/api/token returned no token or LiveKit URL. Check NEXT_PUBLIC_LIVEKIT_URL in .env.");
          }
        } catch (e) {
          setError((e as Error).message || "Could not get a LiveKit token from /api/token.");
          setConnectionDetails(prev => ({ ...prev, mode: "manual" }));
          return;
        }
      }

      setError(null);

      setConnectionDetails({
        wsUrl: url,
        token: token,
        shouldConnect: true,
        mode,
        avatarImage,
      });
    },
    [connectionDetails.shouldConnect, connectionDetails.mode, config.settings.room_name, config.settings.participant_name]
  );

  const disconnect = useCallback(async () => {
    console.log('[connection] Disconnecting...');
    setConnectionDetails({
      wsUrl: "",
      token: "",
      shouldConnect: false,
      mode: "manual",
      avatarImage: "",
    });
  }, []);

  return (
    <ConnectionContext.Provider
      value={{
        wsUrl: connectionDetails.wsUrl,
        token: connectionDetails.token,
        shouldConnect: connectionDetails.shouldConnect,
        mode: connectionDetails.mode,
        avatarImage: connectionDetails.avatarImage,
        roomName,
        error,
        setError,
        connect,
        disconnect,
      }}
    >
      {children}
    </ConnectionContext.Provider>
  );
};

export const useConnection = () => {
  const context = useContext(ConnectionContext);
  if (context === undefined) {
    throw new Error("useConnection must be used within a ConnectionProvider");
  }
  return context;
};

export const useAppConfig = () => {
  // Simple default config for basic functionality
  return {
    title: "Video Chat",
    description: "Simple video chat interface",
    settings: {
      editable: true,
      theme_color: "blue",
      chat: false,
      inputs: {
        camera: true,
        mic: true,
      },
      outputs: {
        audio: true,
        video: true,
      },
      ws_url: "",
      token: "",
      room_name: "default-room",
      participant_name: "user",
    },
  };
};
