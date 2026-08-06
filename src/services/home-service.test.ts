import { describe, expect, it } from "vitest";

import { DEFAULT_ARTWORK_PATH } from "@/services/api-mappers";
import { mapHomeResponse } from "@/services/home-service";

const track = {
  id: "track-id",
  slug: "track-slug",
  title: "पहिलो कथा",
  titleEnglish: "First Story",
  subtitle: "",
  contentType: "story",
  author: {
    id: "author-id",
    slug: "author",
    name: "लेखक",
    nameEnglish: "Author",
    image: null,
  },
  narrator: {
    id: "narrator-id",
    slug: "narrator",
    name: "वाचक",
    image: null,
  },
  coverImage: null,
  duration: 120,
  language: "ne",
  genres: ["story"],
  moods: ["calm"],
  playCount: 10,
  isPremium: false,
  isExplicit: false,
  isFeatured: true,
  publishedAt: "2026-07-29T12:00:00Z",
};

const playlist = {
  id: "playlist-id",
  slug: "featured",
  title: "विशेष सङ्ग्रह",
  coverImage: null,
  curatorName: "SunneKatha",
  trackCount: 4,
  totalDuration: 600,
  category: "editorial",
  isFeatured: true,
};

describe("homepage response adapter", () => {
  it("preserves backend section order and uses explicit editorial presentation", () => {
    const result = mapHomeResponse({
      hero: {
        id: "hero",
        title: "विशेष",
        contentType: "playlist",
        content: playlist,
      },
      sections: [
        {
          id: "editors-selection",
          title: "सम्पादकको रोजाइ",
          subtitle: "आजका उत्कृष्ट रचना",
          sectionType: "tracks",
          layout: "grid",
          items: [track],
        },
        {
          id: "featured-playlists",
          title: "प्लेलिस्ट",
          sectionType: "playlists",
          layout: "rail",
          items: [playlist],
        },
      ],
    });

    expect(result.hero).toMatchObject({
      kind: "playlist",
      content: {
        id: "playlist-id",
        coverImage: DEFAULT_ARTWORK_PATH,
      },
    });
    expect(result.sections.map((section) => section.kind)).toEqual([
      "tracks",
      "playlists",
    ]);
    expect(result.sections.map((section) => section.title)).toEqual([
      "सम्पादकको रोजाइ",
      "प्लेलिस्ट",
    ]);
    expect(result.sections[0]).toMatchObject({
      subtitle: "आजका उत्कृष्ट रचना",
      layout: "grid",
    });
  });

  it("maps personalized continue listening without inventing an audio URL", () => {
    const result = mapHomeResponse({
      hero: null,
      sections: [
        {
          id: "continue-listening",
          title: "सुन्न जारी राख्नुहोस्",
          items: [
            {
              track,
              progress: {
                trackId: "track-id",
                progressSeconds: 30,
                durationSeconds: 120,
                progressPercentage: 25,
                isCompleted: false,
                lastListenedAt: "2026-07-29T12:00:00Z",
                updatedAt: "2026-07-29T12:00:00Z",
              },
            },
          ],
        },
      ],
    });

    const section = result.sections[0];
    expect(section?.kind).toBe("continue-listening");
    if (section?.kind !== "continue-listening") {
      throw new Error("Expected Continue Listening section.");
    }
    expect(section.items[0]?.track).not.toHaveProperty("audioUrl");
    expect(section.items[0]?.progress.progressSeconds).toBe(30);
  });

  it("supports an editorial track hero without inventing an audio URL", () => {
    const result = mapHomeResponse({
      hero: {
        id: "featured-story",
        title: "आजको विशेष",
        contentType: "track",
        content: track,
      },
      sections: [],
    });

    expect(result.hero?.kind).toBe("track");
    if (result.hero?.kind !== "track") {
      throw new Error("Expected track hero.");
    }
    expect(result.hero.content).not.toHaveProperty("audioUrl");
  });

  it("drops malformed items while retaining a valid section", () => {
    const result = mapHomeResponse({
      hero: null,
      sections: [
        {
          id: "trending-tracks",
          title: "लोकप्रिय",
          items: [{ id: "incomplete" }, track],
        },
      ],
    });

    expect(result.sections[0]?.items).toHaveLength(1);
  });

  it("rejects malformed top-level responses", () => {
    expect(() => mapHomeResponse({ hero: null })).toThrow(
      "गृहपृष्ठको उत्तर बुझ्न सकिएन।",
    );
  });
});
