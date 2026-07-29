import {
  authors,
  narrators,
  playlists,
  tracks,
  userLibrary,
} from "@/data";
import { mockApiResponse } from "@/services/mock-api";
import type {
  Author,
  Narrator,
  Playlist,
  Track,
  UserLibrary,
} from "@/types";

export interface LibraryCatalog {
  tracks: Track[];
  playlists: Playlist[];
  authors: Author[];
  narrators: Narrator[];
}

export async function getInitialUserLibrary(): Promise<UserLibrary> {
  return mockApiResponse(userLibrary);
}

export async function getLibraryCatalog(): Promise<LibraryCatalog> {
  return mockApiResponse({
    tracks,
    playlists,
    authors,
    narrators,
  });
}
