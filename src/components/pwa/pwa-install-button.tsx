"use client";

import { Download, Share, X } from "lucide-react";
import { useEffect, useRef, useState } from "react";

import { Button } from "@/components/ui/button";

interface BeforeInstallPromptEvent extends Event {
  prompt: () => Promise<void>;
  userChoice: Promise<{ outcome: "accepted" | "dismissed" }>;
}

function isStandaloneMode() {
  return (
    window.matchMedia("(display-mode: standalone)").matches ||
    ("standalone" in navigator &&
      Boolean((navigator as Navigator & { standalone?: boolean }).standalone))
  );
}

function isIosDevice() {
  return (
    /iphone|ipad|ipod/i.test(navigator.userAgent) ||
    (/macintosh/i.test(navigator.userAgent) && navigator.maxTouchPoints > 1)
  );
}

export function PwaInstallButton() {
  const [installPrompt, setInstallPrompt] =
    useState<BeforeInstallPromptEvent | null>(null);
  const [canShowIosHelp, setCanShowIosHelp] = useState(false);
  const helpDialogRef = useRef<HTMLDialogElement>(null);

  useEffect(() => {
    if ("serviceWorker" in navigator) {
      void navigator.serviceWorker
        .register("/sw.js", { updateViaCache: "none" })
        .then((registration) => registration.update())
        .catch(() => undefined);
    }

    if (isStandaloneMode()) return;

    const detectionFrame = window.requestAnimationFrame(() => {
      setCanShowIosHelp(isIosDevice());
    });

    const handleInstallPrompt = (event: Event) => {
      event.preventDefault();
      setInstallPrompt(event as BeforeInstallPromptEvent);
    };
    const handleInstalled = () => {
      setInstallPrompt(null);
      setCanShowIosHelp(false);
    };

    window.addEventListener("beforeinstallprompt", handleInstallPrompt);
    window.addEventListener("appinstalled", handleInstalled);

    return () => {
      window.cancelAnimationFrame(detectionFrame);
      window.removeEventListener("beforeinstallprompt", handleInstallPrompt);
      window.removeEventListener("appinstalled", handleInstalled);
    };
  }, []);

  const handleInstall = async () => {
    if (installPrompt) {
      await installPrompt.prompt();
      const choice = await installPrompt.userChoice;

      if (choice.outcome === "accepted") {
        setInstallPrompt(null);
      }
      return;
    }

    helpDialogRef.current?.showModal();
  };

  if (!installPrompt && !canShowIosHelp) return null;

  return (
    <>
      <Button
        type="button"
        variant="secondary"
        size="icon"
        onClick={() => void handleInstall()}
        aria-label="SunneKatha एप इन्स्टल गर्नुहोस्"
        className="size-11 shrink-0 rounded-full lg:hidden"
      >
        <Download aria-hidden="true" className="size-[1.1rem]" />
      </Button>

      <dialog
        ref={helpDialogRef}
        aria-labelledby="pwa-install-title"
        className="m-auto w-[calc(100%-2rem)] max-w-sm rounded-2xl border border-border bg-surface p-0 text-foreground shadow-2xl backdrop:bg-black/70"
        onClick={(event) => {
          if (event.target === event.currentTarget) {
            event.currentTarget.close();
          }
        }}
      >
        <div className="relative p-6">
          <Button
            type="button"
            variant="ghost"
            size="icon"
            onClick={() => helpDialogRef.current?.close()}
            aria-label="इन्स्टल निर्देशन बन्द गर्नुहोस्"
            className="absolute top-3 right-3 size-11 rounded-full"
          >
            <X aria-hidden="true" className="size-5" />
          </Button>
          <Share aria-hidden="true" className="size-7 text-primary" />
          <h2
            id="pwa-install-title"
            className="mt-4 pr-10 font-literary text-2xl font-semibold"
          >
            मोबाइलमा SunneKatha राख्नुहोस्
          </h2>
          <ol className="mt-4 space-y-3 font-nepali text-sm leading-6 text-muted-foreground">
            <li>१. Safari को Share बटन थिच्नुहोस्।</li>
            <li>२. “Add to Home Screen” छान्नुहोस्।</li>
            <li>३. माथिल्लो दायाँपट्टि “Add” थिच्नुहोस्।</li>
          </ol>
          <Button
            type="button"
            onClick={() => helpDialogRef.current?.close()}
            className="mt-6 w-full rounded-full font-nepali"
          >
            बुझें
          </Button>
        </div>
      </dialog>
    </>
  );
}
