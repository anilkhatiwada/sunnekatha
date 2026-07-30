import {
  authors,
  genres,
  moods,
  narrators,
  playlists,
  tracks,
} from "@/data";
import { environment } from "@/config/environment";
import {
  mapAuthorSummary,
  mapCompactPlaylist,
  mapCompactTrack,
  mapNarratorSummary,
  mapTaxonomy,
} from "@/services/api-mappers";
import { apiClient } from "@/services/api-client";
import { mockApiResponse } from "@/services/mock-api";
import { unwrapPage } from "@/services/public-api-utils";
import { searchValuesMatch } from "@/services/search-normalizer";
import type {
  ApiAutocompleteItem,
  ApiGroupedSearchResponse,
  ApiTrackPage,
  ApiTrendingSearchResponse,
  Author,
  Narrator,
  SearchRequest,
  SearchResults,
  SearchResultType,
  SearchSuggestion,
  SearchTrackPage,
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
}: SearchRequest, signal?: AbortSignal): Promise<SearchResults> {
  if (!query.trim()) {
    return mockApiResponse(EMPTY_RESULTS);
  }

  if (environment.apiMode === "remote") {
    if (resultType === "tracks") {
      const page = await searchTracks(query, 1, signal);
      return {
        ...EMPTY_RESULTS,
        tracks: page.results,
      };
    }

    const response = await apiClient.get<ApiGroupedSearchResponse>("/search/", {
      query: {
        q: query.trim(),
        type: resultType,
      },
      signal,
    });
    return mapGroupedSearchResponse(response);
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

export async function searchTracks(
  query: string,
  page = 1,
  signal?: AbortSignal,
): Promise<SearchTrackPage> {
  const normalizedQuery = query.trim();
  if (!normalizedQuery) {
    return { results: [], count: 0, nextPage: null };
  }

  if (environment.apiMode === "remote") {
    const response = await apiClient.get<ApiTrackPage>("/search/tracks/", {
      query: { q: normalizedQuery, page },
      signal,
    });
    return {
      results: unwrapPage(response).map(mapCompactTrack),
      count: response.count,
      nextPage: response.next ? page + 1 : null,
    };
  }

  const results = await searchContent({
    query: normalizedQuery,
    resultType: "tracks",
  });
  return {
    results: results.tracks,
    count: results.tracks.length,
    nextPage: null,
  };
}

export async function getTrendingSearches(
  signal?: AbortSignal,
): Promise<string[]> {
  if (environment.apiMode === "remote") {
    const response = await apiClient.get<ApiTrendingSearchResponse>(
      "/search/trending/",
      { signal },
    );
    return response.searches;
  }
  return mockApiResponse(TRENDING_SEARCHES, 150);
}

export async function getSearchSuggestions(
  query: string,
  signal?: AbortSignal,
): Promise<SearchSuggestion[]> {
  const normalizedQuery = query.trim();
  if (!normalizedQuery) return [];

  if (environment.apiMode === "remote") {
    const response = await apiClient.get<ApiAutocompleteItem[]>(
      "/search/autocomplete/",
      { query: { q: normalizedQuery }, signal },
    );
    return response.map((item) => ({
      id: item.id,
      type: item.type,
      slug: item.slug,
      label: item.label,
      labelEnglish: item.labelEnglish || undefined,
    }));
  }

  const results = await searchContent({ query: normalizedQuery });
  return [
    ...results.tracks.map((item) => ({
      id: item.id,
      type: "track",
      slug: item.slug,
      label: item.title,
      labelEnglish: item.subtitle,
    })),
    ...results.authors.map((item) => ({
      id: item.id,
      type: "author",
      slug: item.slug,
      label: item.name,
      labelEnglish: item.nameEnglish,
    })),
    ...results.narrators.map((item) => ({
      id: item.id,
      type: "narrator",
      slug: item.slug,
      label: item.name,
    })),
  ].slice(0, 10);
}

function mapGroupedSearchResponse(
  response: ApiGroupedSearchResponse,
): SearchResults {
  return {
    tracks: response.tracks.map(mapCompactTrack),
    playlists: response.playlists.map(mapCompactPlaylist),
    authors: response.authors.map(mapSearchAuthor),
    narrators: response.narrators.map(mapSearchNarrator),
    genres: response.genres.map(mapTaxonomy),
    moods: response.moods.map(mapTaxonomy),
  };
}

function mapSearchAuthor(value: ApiGroupedSearchResponse["authors"][number]): Author {
  return {
    ...mapAuthorSummary(value),
    biography: "",
    genres: [],
    popularTracks: [],
  };
}

function mapSearchNarrator(
  value: ApiGroupedSearchResponse["narrators"][number],
): Narrator {
  return {
    ...mapNarratorSummary(value),
    biography: "",
    followerCount: value.followerCount ?? 0,
    narratedTracks: [],
  };
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
