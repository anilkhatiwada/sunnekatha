import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { HomePageContent } from "@/features/home/home-page";
import * as services from "@/services";
import type { HomePageData } from "@/types";

vi.mock("framer-motion", async () => {
  const actual = await vi.importActual<typeof import("framer-motion")>(
    "framer-motion",
  );
  return { ...actual, useReducedMotion: () => true };
});

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: vi.fn() }),
}));

function renderHomepage() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return render(
    <QueryClientProvider client={queryClient}>
      <HomePageContent />
    </QueryClientProvider>,
  );
}

describe("remote homepage", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it("renders non-empty sections in backend order", async () => {
    const data: HomePageData = {
      hero: null,
      sections: [
        {
          id: "authors",
          title: "पहिलो खण्ड",
          layout: "rail",
          kind: "authors",
          items: [
            {
              id: "author-id",
              slug: "author",
              name: "लेखक",
              image: "/icons/pwa-192.png",
              biography: "",
              genres: [],
              popularTracks: [],
            },
          ],
        },
        {
          id: "empty",
          title: "खाली खण्ड",
          layout: "rail",
          kind: "tracks",
          items: [],
        },
        {
          id: "narrators",
          title: "दोस्रो खण्ड",
          layout: "rail",
          kind: "narrators",
          items: [
            {
              id: "narrator-id",
              slug: "narrator",
              name: "वाचक",
              image: "/icons/pwa-192.png",
              biography: "",
              followerCount: 10,
              narratedTracks: [],
            },
          ],
        },
      ],
    };
    vi.spyOn(services, "getHomePage").mockResolvedValue(data);

    renderHomepage();

    expect(await screen.findByText("पहिलो खण्ड")).toBeInTheDocument();
    expect(screen.getByText("दोस्रो खण्ड")).toBeInTheDocument();
    expect(screen.queryByText("खाली खण्ड")).not.toBeInTheDocument();
    const headings = screen.getAllByRole("heading", { level: 2 });
    expect(headings.map((heading) => heading.textContent)).toEqual([
      "Featured content is coming",
      "पहिलो खण्ड",
      "दोस्रो खण्ड",
    ]);
  });

  it("shows retry UI and never falls back to demo content", async () => {
    vi.spyOn(services, "getHomePage").mockRejectedValue(
      new Error("backend unavailable"),
    );

    renderHomepage();

    await waitFor(() =>
      expect(screen.getByRole("alert")).toBeInTheDocument(),
    );
    expect(screen.getByText("Try again")).toBeInTheDocument();
    expect(screen.queryByText("प्रेमका कविता")).not.toBeInTheDocument();
  });

  it("renders categories with a link to browse all categories", async () => {
    const data: HomePageData = {
      hero: null,
      sections: [
        {
          id: "browse-categories",
          title: "Browse Categories",
          layout: "grid",
          kind: "categories",
          viewAllHref: "/explore",
          items: [
            {
              id: "story-id",
              slug: "story",
              name: "कथा",
              nameEnglish: "Story",
              description: "कथाहरू",
            },
          ],
        },
      ],
    };
    vi.spyOn(services, "getHomePage").mockResolvedValue(data);

    renderHomepage();

    expect(await screen.findByText("Browse Categories")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "View all" })).toHaveAttribute(
      "href",
      "/explore",
    );
    expect(screen.getByRole("link", { name: /Story/ })).toHaveAttribute(
      "href",
      "/explore?type=story",
    );
  });
});
