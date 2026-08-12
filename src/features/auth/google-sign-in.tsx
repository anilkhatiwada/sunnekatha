"use client";

import { useEffect, useRef, useState } from "react";

import { environment } from "@/config/environment";
import { loginWithGoogle } from "@/services";

declare global {
  interface Window {
    google?: {
      accounts: {
        id: {
          initialize(options: {
            client_id: string;
            callback: (response: { credential?: string }) => void;
          }): void;
          renderButton(
            element: HTMLElement,
            options: Record<string, string | number | (() => void)>,
          ): void;
        };
      };
    };
  }
}

export function GoogleSignIn() {
  const buttonRef = useRef<HTMLDivElement>(null);
  const responseTimerRef = useRef<number | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    if (!environment.googleClientId) return;

    const render = () => {
      if (!window.google || !buttonRef.current) return;
      window.google.accounts.id.initialize({
        client_id: environment.googleClientId,
        callback: async ({ credential }) => {
          if (responseTimerRef.current) {
            window.clearTimeout(responseTimerRef.current);
          }
          if (!credential) {
            setError("Google did not return an identity.");
            return;
          }
          setError("");
          try {
            await loginWithGoogle(credential);
            window.location.assign("/profile");
          } catch {
            setError("Google sign-in failed. Please try again.");
          }
        },
      });
      buttonRef.current.replaceChildren();
      window.google.accounts.id.renderButton(buttonRef.current, {
        type: "standard",
        theme: "filled_black",
        size: "large",
        shape: "pill",
        text: "continue_with",
        width: 320,
        click_listener: () => {
          setError("");
          if (responseTimerRef.current) {
            window.clearTimeout(responseTimerRef.current);
          }
          responseTimerRef.current = window.setTimeout(() => {
            setError(
              "Google did not respond. Check popup permissions and the https://sunnekatha.com origin in Google OAuth.",
            );
          }, 10_000);
        },
      });
    };

    const existing = document.querySelector<HTMLScriptElement>(
      'script[src="https://accounts.google.com/gsi/client"]',
    );
    if (existing) {
      if (window.google) render();
      else existing.addEventListener("load", render, { once: true });
      return;
    }
    const script = document.createElement("script");
    script.src = "https://accounts.google.com/gsi/client";
    script.async = true;
    script.defer = true;
    script.addEventListener("load", render, { once: true });
    document.head.appendChild(script);
    return () => {
      if (responseTimerRef.current) {
        window.clearTimeout(responseTimerRef.current);
      }
    };
  }, []);

  if (!environment.googleClientId) {
    return (
      <p className="font-nepali text-sm text-muted-foreground">
        Google sign-in is not configured.
      </p>
    );
  }

  return (
    <div>
      <div ref={buttonRef} className="flex min-h-11 justify-center" />
      {error ? (
        <p role="alert" className="mt-3 font-nepali text-sm text-destructive">
          {error}
        </p>
      ) : null}
    </div>
  );
}
