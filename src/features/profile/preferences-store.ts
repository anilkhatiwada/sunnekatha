"use client";

import { create } from "zustand";
import { persist } from "zustand/middleware";

import type { ProfilePreferencesFormValues } from "@/features/profile/profile-schema";

export interface ProfilePreferences extends ProfilePreferencesFormValues {
  audioQuality: "automatic";
}

interface PreferencesStore extends ProfilePreferences {
  hasHydrated: boolean;
  setHasHydrated: (hasHydrated: boolean) => void;
  updatePreferences: (preferences: ProfilePreferencesFormValues) => void;
}

const DEFAULT_PREFERENCES: ProfilePreferences = {
  displayName: "अनिल खटिवडा",
  email: "anil@example.com",
  preferredLanguage: "ne",
  autoplay: true,
  defaultPlaybackSpeed: 1,
  audioQuality: "automatic",
  allowExplicitContent: false,
  themePreference: "dark",
};

export const usePreferencesStore = create<PreferencesStore>()(
  persist(
    (set) => ({
      ...DEFAULT_PREFERENCES,
      hasHydrated: false,
      setHasHydrated: (hasHydrated) => set({ hasHydrated }),
      updatePreferences: (preferences) => set(preferences),
    }),
    {
      name: "sunnekatha-preferences",
      onRehydrateStorage: () => (state) => {
        state?.setHasHydrated(true);
      },
      partialize: (state) => ({
        displayName: state.displayName,
        email: state.email,
        preferredLanguage: state.preferredLanguage,
        autoplay: state.autoplay,
        defaultPlaybackSpeed: state.defaultPlaybackSpeed,
        audioQuality: state.audioQuality,
        allowExplicitContent: state.allowExplicitContent,
        themePreference: state.themePreference,
      }),
    },
  ),
);
