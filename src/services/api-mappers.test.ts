import { describe, expect, it } from "vitest";

import {
  DEFAULT_ARTWORK_PATH,
  DEFAULT_AVATAR_PATH,
  mapCompactTrack,
  mapCompactLiteraryWork,
  mapPlayableTrack,
} from "@/services/api-mappers";
import type {
  ApiCompactTrack,
  ApiCompactLiteraryWork,
  ApiStreamResponse,
} from "@/types/backend-api";

const compactTrack: ApiCompactTrack = {
  id: "track-id",
  slug: "test-track",
  title: "परीक्षण कथा",
  titleEnglish: "Test Story",
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
  duration: 180,
  language: "ne",
  genres: ["story"],
  moods: ["calm"],
  playCount: 12,
  isPremium: false,
  isExplicit: false,
  isFeatured: false,
  publishedAt: "2026-07-29T12:00:00Z",
};

describe("backend API mappers", () => {
  it("maps nullable backend artwork to generic application fallbacks", () => {
    const mapped = mapCompactTrack(compactTrack);

    expect(mapped.coverImage).toBe(DEFAULT_ARTWORK_PATH);
    expect(mapped.author.image).toBe(DEFAULT_AVATAR_PATH);
    expect(mapped.narrator.image).toBe(DEFAULT_AVATAR_PATH);
    expect(mapped).not.toHaveProperty("audioUrl");
  });

  it("creates a playable track only from an authorized stream response", () => {
    const response: ApiStreamResponse = {
      quality: "high",
      url: "https://audio.example.com/free/test-track.mp3",
      expiresAt: null,
      track: compactTrack,
      authorization: {
        status: "authorized",
        accessType: "free",
        isEntitled: false,
        isPrivileged: false,
      },
      introduction: {
        url: "https://audio.example.com/free/test-introduction.mp3",
        expiresAt: null,
        duration: 9,
      },
    };

    expect(mapPlayableTrack(response).audioUrl).toBe(response.url);
    expect(mapPlayableTrack(response).introduction?.duration).toBe(9);
  });

  it("maps serialized work discovery metadata without flattening chapters", () => {
    const category = {
      id: "category-id", slug: "novel", name: "उपन्यास", nameEnglish: "Novel",
      description: "", image: null, sortOrder: 1, isActive: true,
    };
    const work: ApiCompactLiteraryWork = {
      id: "work-id", slug: "serialized-work", title: "धारावाहिक उपन्यास",
      titleEnglish: "Serialized Novel", subtitle: "", subtitleEnglish: "",
      contentType: "novel_chapter", category, primaryCategory: category,
      categories: [category], tags: [{ ...category, id: "tag-id", slug: "family", nameEnglish: "Family" }],
      structure: "serialized", author: compactTrack.author, language: "ne",
      genres: ["novel"], moods: ["reflective"], publicationYear: 2026,
      coverImage: null, isFeatured: true, publishedAt: "2026-09-01T00:00:00Z",
      chapterCount: 8, totalDuration: 3600,
    };

    const mapped = mapCompactLiteraryWork(work);

    expect(mapped.structure).toBe("serialized");
    expect(mapped.chapterCount).toBe(8);
    expect(mapped.tags[0]?.slug).toBe("family");
    expect(mapped.tracks).toEqual([]);
  });
});
