"use client";

import { useEffect } from "react";

import { usePlayerStore } from "@/features/player/player-store";
import { usePreferencesStore } from "@/features/profile/preferences-store";

export function PreferencesController() {
  const themePreference = usePreferencesStore(
    (state) => state.themePreference,
  );
  const defaultPlaybackSpeed = usePreferencesStore(
    (state) => state.defaultPlaybackSpeed,
  );

  useEffect(() => {
    const mediaQuery = window.matchMedia("(prefers-color-scheme: dark)");
    const applyTheme = () => {
      const resolvedTheme =
        themePreference === "system"
          ? mediaQuery.matches
            ? "dark"
            : "light"
          : themePreference;

      document.documentElement.dataset.theme = resolvedTheme;
      document.documentElement.style.colorScheme = resolvedTheme;
    };

    applyTheme();
    mediaQuery.addEventListener("change", applyTheme);
    return () => mediaQuery.removeEventListener("change", applyTheme);
  }, [themePreference]);

  useEffect(() => {
    usePlayerStore.getState().setPlaybackSpeed(defaultPlaybackSpeed);
  }, [defaultPlaybackSpeed]);

  return null;
}
