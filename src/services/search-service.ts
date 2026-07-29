import {
  authors,
  genres,
  moods,
  narrators,
  playlists,
  tracks,
} from "@/data";
import { mockApiResponse } from "@/services/mock-api";
import { searchValuesMatch } from "@/services/search-normalizer";
import type {
  SearchRequest,
  SearchResults,
  SearchResultType,
} from "@/types";

const EMPTY_RESULTS: SearchResults = {
  tracks: [],
  playlists: [],
  authors: [],
  narrators: [],
  genres: [],
  moods: [],
};

const TRENDING_SEARCHES = [
  "प्रेमका कविता",
  "वर्षाको साँझ",
  "नेपाली लोककथा",
  "जीवन र दर्शन",
  "बालकथा",
  "शान्त",
];

export async function searchContent({
  query,
  resultType = "all",
}: SearchRequest): Promise<SearchResults> {
  if (!query.trim()) {
    return mockApiResponse(EMPTY_RESULTS);
  }

  const results: SearchResults = {
    tracks: tracks.filter((track) =>
      searchValuesMatch(
        [
          track.title,
          track.subtitle,
          track.description,
          track.author.name,
          track.author.nameEnglish,
          track.narrator.name,
          ...track.genres,
          ...track.moods,
        ],
        query,
      ),
    ),
    playlists: playlists.filter((playlist) =>
      searchValuesMatch(
        [
          playlist.title,
          playlist.description,
          playlist.category,
          playlist.curatorName,
        ],
        query,
      ),
    ),
    authors: authors.filter((author) =>
      searchValuesMatch(
        [
          author.name,
          author.nameEnglish,
          author.biography,
          ...author.genres,
        ],
        query,
      ),
    ),
    narrators: narrators.filter((narrator) =>
      searchValuesMatch([narrator.name, narrator.biography], query),
    ),
    genres: genres.filter((genre) =>
      searchValuesMatch(
        [genre.name, genre.nameEnglish, genre.description],
        query,
      ),
    ),
    moods: moods.filter((mood) =>
      searchValuesMatch(
        [mood.name, mood.nameEnglish, mood.description],
        query,
      ),
    ),
  };

  return mockApiResponse(filterSearchResults(results, resultType));
}

export async function getTrendingSearches(): Promise<string[]> {
  return mockApiResponse(TRENDING_SEARCHES, 150);
}

function filterSearchResults(
  results: SearchResults,
  resultType: SearchResultType,
) {
  if (resultType === "all") return results;

  return {
    ...EMPTY_RESULTS,
    [resultType]: results[resultType],
  };
}
