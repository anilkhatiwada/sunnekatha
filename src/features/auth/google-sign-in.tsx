"use client";

import { useRouter } from "next/navigation";
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
            options: Record<string, string | number>,
          ): void;
        };
      };
    };
  }
}

export function GoogleSignIn() {
  const buttonRef = useRef<HTMLDivElement>(null);
  const router = useRouter();
  const [error, setError] = useState("");

  useEffect(() => {
    if (!environment.googleClientId) return;

    const render = () => {
      if (!window.google || !buttonRef.current) return;
      window.google.accounts.id.initialize({
        client_id: environment.googleClientId,
        callback: async ({ credential }) => {
          if (!credential) {
            setError("Google बाट पहिचान प्राप्त भएन।");
            return;
          }
          setError("");
          try {
            await loginWithGoogle(credential);
            router.replace("/profile");
            router.refresh();
          } catch {
            setError("Google साइन इन सफल भएन। कृपया फेरि प्रयास गर्नुहोस्।");
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
  }, [router]);

  if (!environment.googleClientId) {
    return (
      <p className="font-nepali text-sm text-muted-foreground">
        Google साइन इन अहिले कन्फिगर गरिएको छैन।
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
