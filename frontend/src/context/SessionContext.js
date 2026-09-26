import { jsx as _jsx } from "react/jsx-runtime";
import { createContext, useContext, useState, useCallback, } from "react";
const SessionContext = createContext(null);
export function SessionProvider({ children }) {
    const [session, setSessionState] = useState(null);
    const setSession = useCallback((s) => {
        setSessionState(s);
    }, []);
    const clearSession = useCallback(() => {
        setSessionState(null);
    }, []);
    return (_jsx(SessionContext.Provider, { value: { session, setSession, clearSession }, children: children }));
}
export function useSessionContext() {
    const ctx = useContext(SessionContext);
    if (!ctx) {
        throw new Error("useSessionContext must be used within SessionProvider");
    }
    return ctx;
}
