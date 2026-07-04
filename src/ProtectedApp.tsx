import React from "react";
import App from "./App";
import {
  SignedIn,
  SignedOut,
  SignIn,
  SignOutButton,
  UserButton,
  useUser,
} from "@clerk/clerk-react";

const env = (import.meta as ImportMeta & { env: Record<string, string | undefined> }).env;
const TRUTHY_VALUES = new Set(["1", "true", "yes", "on"]);
let previewWarningLogged = false;

function clean(value: unknown): string {
  return String(value ?? "").trim();
}

function isTruthy(value: unknown): boolean {
  return TRUTHY_VALUES.has(clean(value).toLowerCase());
}

function getAllowedEmails(): Set<string> {
  const raw = clean(env.VITE_ALLOWED_EMAILS);
  return new Set(
    raw
      .split(",")
      .map((value) => value.trim().toLowerCase())
      .filter(Boolean),
  );
}

function getUserEmail(user: ReturnType<typeof useUser>["user"]): string {
  return (
    user?.primaryEmailAddress?.emailAddress?.toLowerCase()
    || user?.emailAddresses?.[0]?.emailAddress?.toLowerCase()
    || ""
  );
}

function isLocalPreviewHost(): boolean {
  if (typeof window === "undefined") {
    return false;
  }

  const host = window.location.hostname.toLowerCase();
  return host === "localhost" || host === "127.0.0.1" || host === "::1";
}

function isPreviewQueryEnabled(): boolean {
  if (typeof window === "undefined") {
    return false;
  }

  const params = new URLSearchParams(window.location.search);
  return isTruthy(params.get("dev-bypass")) || isTruthy(params.get("dev-preview"));
}

function isPreviewEnvEnabled(): boolean {
  return isTruthy(env.VITE_EDGEIQ_DEV_PREVIEW);
}

function isDeveloperPreviewMode(): boolean {
  if (!env.DEV) {
    return false;
  }

  if (!isLocalPreviewHost()) {
    return false;
  }

  if (isPreviewQueryEnabled()) {
    return true;
  }

  return false;
}

function getPreviewActivationSummary(): string {
  const queryMode = isPreviewQueryEnabled() ? "query-param" : "none";
  const envMode = isPreviewEnvEnabled() ? "env-flag" : "no-env-flag";
  return `${queryMode}; ${envMode}`;
}

function DevPreviewShell(): React.ReactElement {
  React.useEffect(() => {
    if (previewWarningLogged) {
      return;
    }

    previewWarningLogged = true;
    console.warn(
      `[EDGEIQ DEV PREVIEW] Local auth bypass active on localhost. Visual QA only. Activation=${getPreviewActivationSummary()}. Production Clerk flow is unchanged.`,
    );
  }, []);

  return <App />;
}

function LockedApp(): React.ReactElement {
  const { isLoaded, user } = useUser();
  const allowedEmails = getAllowedEmails();

  if (!isLoaded) {
    return (
      <div className="min-h-screen bg-[#0f0f10] text-white flex items-center justify-center">
        <div className="rounded-md border border-[#2a2a2a] bg-[#171717] px-6 py-5 text-[15px] text-[#d8d8d8]">
          Loading secure terminal...
        </div>
      </div>
    );
  }

  const email = getUserEmail(user);
  const allowed = allowedEmails.has(email);

  if (!allowed) {
    return (
      <div className="min-h-screen bg-[#0f0f10] text-white flex items-center justify-center px-4">
        <div className="w-full max-w-[560px] rounded-md border border-[#4a2323] bg-[#1b1111] p-6 shadow-[0_20px_60px_rgba(0,0,0,0.45)]">
          <div className="text-[11px] uppercase tracking-[0.20em] text-[#d9a2a2]">
            Access blocked
          </div>
          <div className="mt-2 text-[26px] font-semibold tracking-tight text-white">
            This account is not approved
          </div>
          <div className="mt-3 text-[14px] leading-6 text-[#f0caca]">
            Signed in as: {email || "unknown"}
          </div>
          <div className="mt-2 text-[14px] leading-6 text-[#d9b7b7]">
            Only approved email addresses can use this terminal.
          </div>

          <div className="mt-5 flex items-center gap-3">
            <SignOutButton>
              <button className="rounded-sm border border-[#6b2a2a] bg-[#6b2a2a] px-4 py-2 text-[13px] font-medium text-white">
                Sign out
              </button>
            </SignOutButton>
          </div>
        </div>
      </div>
    );
  }

  return (
    <>
      <div className="fixed right-4 top-4 z-50 flex items-center gap-3">
        <div className="rounded-sm border border-[#2a2a2a] bg-[#171717] px-3 py-2 text-[12px] text-[#d8d8d8]">
          {email}
        </div>
        <UserButton afterSignOutUrl="/" />
      </div>
      <App />
    </>
  );
}

export default function ProtectedApp(): React.ReactElement {
  if (isDeveloperPreviewMode()) {
    return <DevPreviewShell />;
  }

  return (
    <>
      <SignedOut>
        <div className="min-h-screen bg-[#0f0f10] text-white flex items-center justify-center px-4">
          <div className="w-full max-w-[440px] rounded-md border border-[#2a2a2a] bg-[#171717] p-5 shadow-[0_20px_60px_rgba(0,0,0,0.45)]">
            <div className="mb-4 text-center">
              <div className="text-[11px] uppercase tracking-[0.22em] text-[#8e8e8e]">
                EDGEiQ RACING
              </div>
              <div className="mt-2 text-[24px] font-semibold tracking-tight text-white">
                Secure Sign In
              </div>
            </div>
            <div className="flex justify-center">
              <SignIn routing="hash" />
            </div>
          </div>
        </div>
      </SignedOut>

      <SignedIn>
        <LockedApp />
      </SignedIn>
    </>
  );
}
