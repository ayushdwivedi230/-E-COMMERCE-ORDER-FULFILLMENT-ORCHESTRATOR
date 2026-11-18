import { useEffect, useRef, useState, useCallback } from "react";

export interface WebSocketMessage {
  type: "ORDER_PROCESSED" | "ORDER_OVERRIDDEN" | "ORDER_REJECTED" | string;
  data: any;
}

function getWebSocketUrl(): string {
  if (import.meta.env.VITE_WS_URL) {
    return import.meta.env.VITE_WS_URL;
  }
  if (import.meta.env.VITE_API_URL) {
    const wsProto = import.meta.env.VITE_API_URL.startsWith("https") ? "wss" : "ws";
    const host = import.meta.env.VITE_API_URL.replace(/^https?:\/\//, "").replace(/\/$/, "");
    return `${wsProto}://${host}/ws/orders`;
  }
  return "ws://localhost:8000/ws/orders";
}

export function useOrderWebSocket(onEvent?: (msg: WebSocketMessage) => void) {
  const [isConnected, setIsConnected] = useState<boolean>(false);
  const [lastEvent, setLastEvent] = useState<WebSocketMessage | null>(null);
  const wsRef = useRef<WebSocket | null>(null);
  const callbackRef = useRef(onEvent);

  useEffect(() => {
    callbackRef.current = onEvent;
  }, [onEvent]);

  const connect = useCallback(() => {
    try {
      const ws = new WebSocket(getWebSocketUrl());
      wsRef.current = ws;

      ws.onopen = () => {
        setIsConnected(true);
      };

      ws.onmessage = (event) => {
        try {
          const parsed: WebSocketMessage = JSON.parse(event.data);
          setLastEvent(parsed);
          if (callbackRef.current) {
            callbackRef.current(parsed);
          }
        } catch {
          // ignore ping/pong or raw strings
        }
      };

      ws.onclose = () => {
        setIsConnected(false);
        // Attempt reconnection after 3 seconds
        setTimeout(connect, 3000);
      };

      ws.onerror = () => {
        ws.close();
      };
    } catch {
      setIsConnected(false);
    }
  }, []);

  useEffect(() => {
    connect();
    return () => {
      if (wsRef.current) {
        wsRef.current.close();
      }
    };
  }, [connect]);

  return { isConnected, lastEvent };
}
