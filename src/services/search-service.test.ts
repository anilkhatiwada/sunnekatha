import { describe, expect, it } from "vitest";

import { searchContent } from "@/services/search-service";

describe("search filtering", () => {
  it("finds Nepali Unicode and Romanized queries", async () => {
    const nepaliResults = await searchContent({ query: "वर्षाको साँझ" });
    const romanizedResults = await searchContent({
      query: "barshako saanjh",
    });

    expect(nepaliResults.tracks.length + nepaliResults.playlists.length).toBeGreaterThan(0);
    expect(
      romanizedResults.tracks.length + romanizedResults.playlists.length,
    ).toBeGreaterThan(0);
  });

  it("limits results to the selected content type", async () => {
    const results = await searchContent({
      query: "कथा",
      resultType: "tracks",
    });

    expect(results.tracks.length).toBeGreaterThan(0);
    expect(results.playlists).toEqual([]);
    expect(results.authors).toEqual([]);
    expect(results.narrators).toEqual([]);
  });
});
