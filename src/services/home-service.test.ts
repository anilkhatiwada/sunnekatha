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

const serializedWork = {
  id: "work-id",
  slug: "serialized-work",
  title: "क्रमिक उपन्यास",
  titleEnglish: "Serialized Novel",
  contentType: "Novel",
  structure: "serialized",
  author: track.author,
  category: null,
  primaryCategory: null,
  categories: [],
  coverImage: null,
  genres: [],
  moods: [],
  tags: [],
  isFeatured: false,
  publishedAt: "2026-07-30T12:00:00Z",
  chapterCount: 6,
  totalDuration: 3600,
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
      "Featured Audio",
      "Featured Playlists",
    ]);
    expect(result.sections[0]).toMatchObject({
      subtitle: "Editorial selections from this category.",
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

  it("preserves serialized parents in legacy track-labelled sections", () => {
    const result = mapHomeResponse({
      hero: null,
      sections: [
        {
          id: "new-releases",
          title: "नयाँ सार्वजनिक रचना",
          sectionType: "tracks",
          items: [serializedWork, track],
        },
      ],
    });

    expect(result.sections[0]?.kind).toBe("catalog");
    if (result.sections[0]?.kind !== "catalog") return;
    expect(result.sections[0].items.map((item) => item.kind)).toEqual([
      "work",
      "track",
    ]);
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

  it("maps editorial category sections for the explore category filter", () => {
    const result = mapHomeResponse({
      hero: null,
      sections: [
        {
          id: "browse-categories",
          title: "विधाअनुसार अन्वेषण",
          sectionType: "categories",
          layout: "grid",
          items: [
            {
              id: "category-id",
              slug: "story",
              title: "कथा",
              titleEnglish: "Story",
              coverImage: null,
              description: "कथाहरू",
            },
          ],
        },
      ],
    });

    expect(result.sections[0]).toMatchObject({
      kind: "categories",
      layout: "grid",
      items: [
        {
          id: "category-id",
          slug: "story",
          name: "Story",
        },
      ],
    });
  });

  it("preserves category artwork for the category icon", () => {
    const result = mapHomeResponse({
      hero: null,
      sections: [
        {
          id: "categories",
          title: "विधाहरू",
          sectionType: "categories",
          items: [
            {
              id: "poetry-id",
              slug: "poetry",
              title: "कविता",
              coverImage: "https://media.sunnekatha.com/covers/poetry.jpg",
            },
          ],
        },
      ],
    });

    expect(result.sections[0]?.items[0]).toMatchObject({
      name: "Poetry",
      image: "https://media.sunnekatha.com/covers/poetry.jpg",
    });
  });

  it("maps safe view-all links for writers and category track sections", () => {
    const result = mapHomeResponse({
      hero: null,
      sections: [
        {
          id: "poetry-picks",
          title: "कविताका रोजाइ",
          sectionType: "tracks",
          browseCategory: { slug: "poetry", name: "कविता" },
          items: [track],
        },
        {
          id: "writers",
          title: "सर्जकका स्वरहरू",
          sectionType: "authors",
          items: [],
        },
      ],
    });

    expect(result.sections[0]?.viewAllHref).toBe("/explore?type=poetry");
    expect(result.sections[1]?.viewAllHref).toBe("/authors");
  });

  it("rejects malformed top-level responses", () => {
    expect(() => mapHomeResponse({ hero: null })).toThrow(
      "The homepage response could not be processed.",
    );
  });
});
