"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { ListMusic, Plus, X } from "lucide-react";
import { useState } from "react";

import { PlaylistCard, PlaylistCardSkeleton } from "@/components/cards";
import { EmptyState } from "@/components/common/empty-state";
import { SectionError } from "@/components/common/section-error";
import { Button } from "@/components/ui/button";
import { useAuth } from "@/features/auth/auth-provider";
import { useCatalogPlayback } from "@/features/player/use-catalog-playback";
import {
  createPlaylist,
  getMyPlaylists,
  getPublicPlaylists,
  queryKeys,
} from "@/services";

const inputClassName =
  "h-11 w-full rounded-lg border border-border bg-background/60 px-3 font-nepali text-sm text-foreground focus:border-primary focus:outline-2 focus:outline-primary";

export function PlaylistsPageContent() {
  const { user } = useAuth();
  const queryClient = useQueryClient();
  const { playPlaylist } = useCatalogPlayback();
  const [isCreating, setIsCreating] = useState(false);
  const [title, setTitle] = useState("");
  const [visibility, setVisibility] = useState<"private" | "unlisted">(
    "private",
  );
  const publicQuery = useQuery({
    queryKey: queryKeys.playlists.public(),
    queryFn: getPublicPlaylists,
    staleTime: 60_000,
  });
  const mineQuery = useQuery({
    queryKey: queryKeys.playlists.mine(),
    queryFn: getMyPlaylists,
    enabled: Boolean(user),
    staleTime: 15_000,
  });
  const createMutation = useMutation({
    mutationFn: () =>
      createPlaylist({
        titleNe: title.trim(),
        visibility,
      }),
    onSuccess: async () => {
      setTitle("");
      setVisibility("private");
      setIsCreating(false);
      await Promise.all([
        queryClient.invalidateQueries({
          queryKey: queryKeys.playlists.mine(),
        }),
        queryClient.invalidateQueries({
          queryKey: queryKeys.playlists.public(),
        }),
      ]);
    },
  });

  if (publicQuery.isError) {
    return (
      <SectionError
        message="Playlists could not be loaded. Please try again."
        onRetry={() => void publicQuery.refetch()}
        isRetrying={publicQuery.isFetching}
      />
    );
  }

  return (
    <div className="space-y-12 pb-8">
      <header className="relative overflow-hidden rounded-2xl border border-border bg-surface/75 px-5 py-9 sm:px-8 sm:py-12">
        <div className="absolute inset-0 bg-[radial-gradient(circle_at_top_left,rgb(229_138_82_/_0.18),transparent_34rem)]" />
        <div className="relative flex flex-wrap items-end justify-between gap-6">
          <div>
            <p className="font-nepali text-xs font-semibold text-primary">
              Collections ready to play
            </p>
            <h1 className="mt-2 font-literary text-4xl font-semibold sm:text-5xl">
              Playlist
            </h1>
            <p className="mt-3 max-w-2xl font-nepali text-sm leading-7 text-muted-foreground">
              Editorial picks and your personal collections in one place.
            </p>
          </div>
          {user ? (
            <Button
              type="button"
              onClick={() => setIsCreating((value) => !value)}
              className="rounded-full font-nepali"
            >
              {isCreating ? (
                <X aria-hidden="true" className="size-4" />
              ) : (
                <Plus aria-hidden="true" className="size-4" />
              )}
              {isCreating ? "Close" : "New playlist"}
            </Button>
          ) : null}
        </div>
      </header>

      {isCreating ? (
        <form
          onSubmit={(event) => {
            event.preventDefault();
            if (title.trim().length >= 2) createMutation.mutate();
          }}
          className="rounded-2xl border border-primary/25 bg-surface p-5 sm:p-7"
        >
          <h2 className="font-literary text-2xl font-semibold">
            New playlist
          </h2>
          <div className="mt-5 grid gap-4 sm:grid-cols-[minmax(0,1fr)_12rem_auto] sm:items-end">
            <label className="font-nepali text-sm">
              Title
              <input
                value={title}
                onChange={(event) => setTitle(event.target.value)}
                minLength={2}
                maxLength={250}
                required
                className={`${inputClassName} mt-2`}
              />
            </label>
            <label className="font-nepali text-sm">
              Visibility
              <select
                value={visibility}
                onChange={(event) =>
                  setVisibility(
                    event.target.value as "private" | "unlisted",
                  )
                }
                className={`${inputClassName} mt-2`}
              >
                <option value="private">Private</option>
                <option value="unlisted">Unlisted</option>
              </select>
            </label>
            <Button
              type="submit"
              disabled={title.trim().length < 2 || createMutation.isPending}
              className="h-11 rounded-full font-nepali"
            >
              {createMutation.isPending ? "Creating…" : "Create"}
            </Button>
          </div>
          {createMutation.isError ? (
            <p role="alert" className="mt-3 font-nepali text-sm text-destructive">
              The playlist could not be created. Check the title and permissions, then try again.
            </p>
          ) : null}
        </form>
      ) : null}

      {user ? (
        <PlaylistGrid
          title="My playlists"
          eyebrow="Personal collections"
          isPending={mineQuery.isPending}
          playlists={mineQuery.data ?? []}
          emptyDescription="Create your first playlist and add a favorite track."
          onPlay={(playlist) => void playPlaylist(playlist)}
        />
      ) : (
        <section className="rounded-2xl border border-dashed border-border bg-surface/40 p-6">
          <h2 className="font-literary text-2xl font-semibold">
            Create your own playlist
          </h2>
          <p className="mt-2 font-nepali text-sm text-muted-foreground">
            Sign in to create private collections and keep them across devices.
          </p>
          <Button
            type="button"
            onClick={() => window.location.assign("/login")}
            className="mt-5 rounded-full font-nepali"
          >
            Sign in
          </Button>
        </section>
      )}

      <PlaylistGrid
        title="Public Playlists"
        eyebrow="SunneKatha editorial"
        isPending={publicQuery.isPending}
        playlists={publicQuery.data ?? []}
        emptyDescription="SunneKatha editorial playlists will appear here."
        onPlay={(playlist) => void playPlaylist(playlist)}
      />
    </div>
  );
}

function PlaylistGrid({
  title,
  eyebrow,
  playlists,
  isPending,
  emptyDescription,
  onPlay,
}: {
  title: string;
  eyebrow: string;
  playlists: Awaited<ReturnType<typeof getPublicPlaylists>>;
  isPending: boolean;
  emptyDescription: string;
  onPlay: (playlist: Awaited<ReturnType<typeof getPublicPlaylists>>[number]) => void;
}) {
  return (
    <section>
      <p className="text-xs font-semibold tracking-[0.16em] text-primary uppercase">
        {eyebrow}
      </p>
      <h2 className="mt-1 font-literary text-3xl font-semibold">{title}</h2>
      {isPending ? (
        <div className="mt-5 grid grid-cols-2 gap-2 sm:grid-cols-3 xl:grid-cols-4">
          {Array.from({ length: 8 }, (_, index) => (
            <PlaylistCardSkeleton key={index} />
          ))}
        </div>
      ) : playlists.length > 0 ? (
        <div className="mt-5 grid grid-cols-2 gap-2 sm:grid-cols-3 xl:grid-cols-4">
          {playlists.map((playlist) => (
            <PlaylistCard
              key={playlist.id}
              playlist={playlist}
              onPlay={onPlay}
            />
          ))}
        </div>
      ) : (
        <EmptyState
          compact
          icon={ListMusic}
          title="Nothing here yet"
          description={emptyDescription}
          className="mt-5"
        />
      )}
    </section>
  );
}
