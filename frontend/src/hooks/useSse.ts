import { useEffect, useRef, useState } from "react";

export function useSse(onEvent: (event: string, data: any) => void) {
  const [connected, setConnected] = useState(false);
  const handler = useRef(onEvent);
  handler.current = onEvent;

  useEffect(() => {
    const es = new EventSource("/api/events");
    es.onopen = () => {
      setConnected(true);
      handler.current("connected", {});
    };
    (["risk_alert", "transaction_alert", "system_alert", "loan_risk_changed", "tool_step", "health"] as const).forEach(
      (name) => {
        es.addEventListener(name, (raw: any) => {
          try {
            handler.current(name, JSON.parse(raw.data));
          } catch {
            handler.current(name, raw.data);
          }
        });
      }
    );
    es.onerror = () => {
      setConnected(false);
      handler.current("error", {});
    };
    return () => es.close();
  }, []);

  return { connected };
}
