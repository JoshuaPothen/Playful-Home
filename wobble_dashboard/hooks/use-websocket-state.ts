'use client';
import { useEffect, useRef, useState } from 'react';
import { WS_URL } from '@/lib/constants';
import type { WobbleState, TriggerEvent } from '@/lib/types';

const RECONNECT_BASE_MS = 1000;
const RECONNECT_MAX_MS  = 30_000;

export function useWebSocketState() {
  const [state, setState]             = useState<WobbleState | null>(null);
  const [lastTrigger, setLastTrigger] = useState<TriggerEvent | null>(null);
  const wsRef      = useRef<WebSocket | null>(null);
  const attemptRef = useRef(0);
  const timerRef   = useRef<ReturnType<typeof setTimeout> | null>(null);
  const deadRef    = useRef(false);

  useEffect(() => {
    deadRef.current = false;

    function connect() {
      if (deadRef.current) return;
      const ws = new WebSocket(WS_URL);
      wsRef.current = ws;

      ws.onopen = () => { attemptRef.current = 0; };

      ws.onmessage = (evt) => {
        let msg: Record<string, unknown>;
        try { msg = JSON.parse(evt.data as string); } catch { return; }
        if (msg.event === 'state') {
          const { event: _e, ...stateData } = msg;
          setState(stateData as unknown as WobbleState);
        } else if (msg.event === 'trigger') {
          setLastTrigger({ type: msg.type } as unknown as TriggerEvent);
        }
      };

      ws.onclose = () => {
        if (deadRef.current) return;
        const delay = Math.min(RECONNECT_BASE_MS * 2 ** attemptRef.current, RECONNECT_MAX_MS);
        attemptRef.current += 1;
        timerRef.current = setTimeout(connect, delay);
      };

      ws.onerror = () => ws.close();
    }

    connect();
    return () => {
      deadRef.current = true;
      if (timerRef.current) clearTimeout(timerRef.current);
      wsRef.current?.close();
    };
  }, []);

  return { state, lastTrigger };
}
