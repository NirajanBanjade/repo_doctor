import { jsx as _jsx } from "react/jsx-runtime";
import { StrictMode } from "react";
import ReactDOM from "react-dom/client";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { SessionProvider } from "@/context/SessionContext";
import App from "./App";
import "@/styles/global.css";
const qc = new QueryClient({
    defaultOptions: {
        queries: {
            staleTime: 10_000,
            retry: 1,
        },
    },
});
ReactDOM.createRoot(document.getElementById("root")).render(_jsx(StrictMode, { children: _jsx(QueryClientProvider, { client: qc, children: _jsx(SessionProvider, { children: _jsx(App, {}) }) }) }));
