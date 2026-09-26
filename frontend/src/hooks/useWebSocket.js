import { useEffect, useRef, useCallback } from "react";
export function useWebSocket(sessionId, onEvent) {
    const wsRef = useRef(null);
    const handlerRef = useRef(onEvent);
    handlerRef.current = onEvent;
    const connect = useCallback(() => {
        if (!sessionId)
            return;
        const protocol = location.protocol === "https:" ? "wss" : "ws";
        const url = `${protocol}://${location.host}/ws/sessions/${sessionId}/events`;
        const ws = new WebSocket(url);
        ws.onmessage = (msg) => {
            try {
                const event = JSON.parse(msg.data);
                handlerRef.current(event);
            }
            catch {
                // non-JSON frame — ignore
            }
        };
        ws.onclose = () => {
            // Reconnect after 3 s if the component is still mounted
            setTimeout(() => {
                if (wsRef.current === ws) {
                    connect();
                }
            }, 3000);
        };
        wsRef.current = ws;
    }, [sessionId]);
    useEffect(() => {
        connect();
        return () => {
            const ws = wsRef.current;
            wsRef.current = null;
            ws?.close();
        };
    }, [connect]);
}
