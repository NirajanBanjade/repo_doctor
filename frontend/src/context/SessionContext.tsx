import {
  createContext,
  useContext,
  useState,
  useCallback,
  type ReactNode,
} from "react";
import type { Session } from "@/types";

interface SessionContextValue {
  session: Session | null;
  setSession: (s: Session | null) => void;
  clearSession: () => void;
}

const SessionContext = createContext<SessionContextValue | null>(null);

export function SessionProvider({ children }: { children: ReactNode }) {
  const [session, setSessionState] = useState<Session | null>(null);

  const setSession = useCallback((s: Session | null) => {
    setSessionState(s);
  }, []);

  const clearSession = useCallback(() => {
    setSessionState(null);
  }, []);

  return (
    <SessionContext.Provider value={{ session, setSession, clearSession }}>
      {children}
    </SessionContext.Provider>
  );
}

export function useSessionContext(): SessionContextValue {
  const ctx = useContext(SessionContext);
  if (!ctx) {
    throw new Error("useSessionContext must be used within SessionProvider");
  }
  return ctx;
}
