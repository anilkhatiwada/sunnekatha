"use client";

import { create } from "zustand";
import { persist } from "zustand/middleware";

const MAX_SEARCH_HISTORY_ITEMS = 8;

interface SearchHistoryStore {
  searches: string[];
  addSearch: (query: string) => void;
  clearHistory: () => void;
}

export const useSearchHistoryStore = create<SearchHistoryStore>()(
  persist(
    (set) => ({
      searches: [],
      addSearch: (query) => {
        const normalizedQuery = query.trim();
        if (!normalizedQuery) return;

        set((state) => ({
          searches: [
            normalizedQuery,
            ...state.searches.filter(
              (item) =>
                item.toLocaleLowerCase() !==
                normalizedQuery.toLocaleLowerCase(),
            ),
          ].slice(0, MAX_SEARCH_HISTORY_ITEMS),
        }));
      },
      clearHistory: () => set({ searches: [] }),
    }),
    {
      name: "sunnekatha-search-history",
      partialize: (state) => ({ searches: state.searches }),
    },
  ),
);
