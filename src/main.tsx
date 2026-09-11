import "./components/shell/edgeiqOsShell.css";
import React from "react";
import ReactDOM from "react-dom/client";
import { ClerkProvider } from "@clerk/clerk-react";
import App from "./App";
import ProtectedApp from "./ProtectedApp";
import "./index.css";
import "./terminal/layout/racing-terminal-overrides.css";
import "./styles/edgeiqDesignSystem.css";
import "./edgeiq-os/design-system/edgeiqDesignSystem.css";
import "./edgeiq-os/approved-ui/edgeiqApprovedUiRebuildV1.css";
import "./edgeiq-os/styles/edgeiqSoftwareSystem.css";

const env = (import.meta as ImportMeta & { env: Record<string, string | undefined> }).env;
const publishableKey = env.VITE_CLERK_PUBLISHABLE_KEY;
const isDev = Boolean((import.meta as ImportMeta & { env: { DEV?: boolean } }).env.DEV);
const disableDevAuth = isDev && env.VITE_DISABLE_AUTH === "true";

if (!publishableKey) {
  console.warn("Clerk disabled: missing VITE_CLERK_PUBLISHABLE_KEY");
}

const root = document.getElementById("root");

if (!root) {
  throw new Error("Missing #root mount point");
}

ReactDOM.createRoot(root).render(
  <React.StrictMode>
    {disableDevAuth ? (
      <App />
    ) : publishableKey ? (
      <ClerkProvider publishableKey={publishableKey}>
        <ProtectedApp />
      </ClerkProvider>
    ) : (
      <App />
    )}
  </React.StrictMode>,
);
