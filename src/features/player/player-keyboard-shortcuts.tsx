"use client";

import { useEffect } from "react";

import {
  pauseAudioImmediately,
  playAudioFromUserGesture,
} from "@/features/player/audio-engine";
import { usePlayerStore } from "@/features/player/player-store";

const EDITABLE_SELECTOR = [
  "input",
  "textarea",
  "select",
  "[contenteditable='true']",
  "[role='textbox']",
  "[role='searchbox']",
  "[role='combobox']",
  "[role='slider']",
  "[role='spinbutton']",
].join(",");

const INTERACTIVE_SELECTOR = [
  EDITABLE_SELECTOR,
  "button",
  "a[href]",
  "[role='button']",
  "[role='link']",
  "[role='menuitem']",
  "[role='tab']",
].join(",");

function isWithin(target: EventTarget | null, selector: string) {
  return target instanceof Element && Boolean(target.closest(selector));
}

export function PlayerKeyboardShortcuts() {
  useEffect(() => {
    const handleKeyDown = (event: KeyboardEvent) => {
      if (
        event.defaultPrevented ||
        event.metaKey ||
        event.ctrlKey ||
        event.altKey
      ) {
        return;
      }

      const state = usePlayerStore.getState();
      const key = event.key.toLowerCase();
      const isEditable = isWithin(event.target, EDITABLE_SELECTOR);
      const isInteractive = isWithin(event.target, INTERACTIVE_SELECTOR);

      if (event.code === "Space") {
        if (isInteractive || !state.currentTrack || event.repeat) return;

        event.preventDefault();
        state.togglePlay();
        if (state.isPlaying) {
          pauseAudioImmediately();
        } else {
          void playAudioFromUserGesture().catch(() => undefined);
        }
        return;
      }

      if (event.key === "ArrowRight" || event.key === "ArrowLeft") {
        if (isInteractive || !state.currentTrack) return;

        event.preventDefault();
        const offset = event.key === "ArrowRight" ? 10 : -10;
        state.seek(state.currentTime + offset);
        return;
      }

      if (isEditable || event.repeat) return;

      if (key === "m") {
        event.preventDefault();
        state.toggleMuted();
      } else if (key === "n" && state.currentTrack) {
        event.preventDefault();
        state.next();
      } else if (key === "p" && state.currentTrack) {
        event.preventDefault();
        state.previous();
      }
    };

    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, []);

  return null;
}
