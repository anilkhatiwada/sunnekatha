"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { useAuth } from "@/features/auth/auth-provider";
import {
  getRemoteUserLibrary,
  queryKeys,
  updateLibraryRelationship,
} from "@/services";
import type { LibraryRelationship } from "@/services";
import type { RemoteUserLibrary } from "@/types";

const COLLECTION_KEYS: Record<
  LibraryRelationship,
  keyof Pick<
    RemoteUserLibrary,
    | "favoriteTracks"
    | "savedPlaylists"
    | "followedAuthors"
    | "followedNarrators"
  >
> = {
  favoriteTrack: "favoriteTracks",
  savedPlaylist: "savedPlaylists",
  followedAuthor: "followedAuthors",
  followedNarrator: "followedNarrators",
};

export function useLibraryRelationship(
  relationship: LibraryRelationship,
  id: string | undefined,
) {
  const { user } = useAuth();
  const queryClient = useQueryClient();
  const libraryQuery = useQuery({
    queryKey: queryKeys.library.remote(),
    queryFn: getRemoteUserLibrary,
    enabled: Boolean(user),
    staleTime: 30_000,
  });
  const collectionKey = COLLECTION_KEYS[relationship];
  const isActive = Boolean(
    id &&
      libraryQuery.data?.[collectionKey].some((item) => item.id === id),
  );
  const mutation = useMutation({
    mutationFn: async (nextIsActive: boolean) => {
      if (!id) throw new Error("A relationship target is required.");
      return updateLibraryRelationship(relationship, id, nextIsActive);
    },
    onMutate: async (nextIsActive) => {
      await queryClient.cancelQueries({
        queryKey: queryKeys.library.remote(),
      });
      const previous = queryClient.getQueryData<RemoteUserLibrary>(
        queryKeys.library.remote(),
      );
      if (!previous || !id) return { previous };

      const existing = previous[collectionKey];
      const target = existing.find((item) => item.id === id);
      queryClient.setQueryData<RemoteUserLibrary>(
        queryKeys.library.remote(),
        {
          ...previous,
          [collectionKey]: nextIsActive
            ? target
              ? existing
              : existing
            : existing.filter((item) => item.id !== id),
        },
      );
      return { previous };
    },
    onError: (_error, _nextIsActive, context) => {
      if (context?.previous) {
        queryClient.setQueryData(
          queryKeys.library.remote(),
          context.previous,
        );
      }
    },
    onSettled: () =>
      queryClient.invalidateQueries({
        queryKey: queryKeys.library.remote(),
      }),
  });

  return {
    isAuthenticated: Boolean(user),
    isActive: mutation.isPending ? Boolean(mutation.variables) : isActive,
    isLoading: libraryQuery.isPending && Boolean(user),
    isPending: mutation.isPending,
    error: mutation.error,
    toggle: () => {
      if (!user || !id || mutation.isPending) return false;
      mutation.mutate(!isActive);
      return true;
    },
  };
}
