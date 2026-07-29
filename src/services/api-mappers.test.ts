import { describe, expect, it } from "vitest";

import {
  DEFAULT_ARTWORK_PATH,
  DEFAULT_AVATAR_PATH,
  mapCompactTrack,
  mapPlayableTrack,
} from "@/services/api-mappers";
import type {
  ApiCompactTrack,
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
    };

    expect(mapPlayableTrack(response).audioUrl).toBe(response.url);
  });
});
