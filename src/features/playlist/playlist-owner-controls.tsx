"use client";

import { useMutation, useQueryClient } from "@tanstack/react-query";
import { ArrowDown, ArrowUp, Copy, Save, Trash2, X } from "lucide-react";
import { useRouter } from "next/navigation";
import { useState } from "react";

import { Button } from "@/components/ui/button";
import {
  deletePlaylist,
  duplicatePlaylist,
  queryKeys,
  removeTrackFromPlaylist,
  reorderPlaylistTracks,
  updatePlaylist,
} from "@/services";
import type { CatalogPlaylist } from "@/types";

export function PlaylistOwnerControls({
  playlist,
}: {
  playlist: CatalogPlaylist;
}) {
  const queryClient = useQueryClient();
  const router = useRouter();
  const [title, setTitle] = useState(playlist.title);
  const [visibility, setVisibility] = useState<"private" | "unlisted">(
    playlist.visibility === "unlisted" ? "unlisted" : "private",
  );
  const [message, setMessage] = useState("");
  const invalidate = () =>
    Promise.all([
      queryClient.invalidateQueries({
        queryKey: queryKeys.playlists.detail(playlist.slug),
      }),
      queryClient.invalidateQueries({ queryKey: queryKeys.playlists.mine() }),
      queryClient.invalidateQueries({ queryKey: queryKeys.playlists.public() }),
    ]);
  const edit = useMutation({
    mutationFn: () =>
      updatePlaylist(playlist.slug, {
        titleNe: title.trim(),
        visibility,
      }),
    onSuccess: async () => {
      setMessage("Playlist changes were saved.");
      await invalidate();
    },
  });
  const remove = useMutation({
    mutationFn: (trackId: string) =>
      removeTrackFromPlaylist(playlist.slug, trackId),
    onSuccess: invalidate,
  });
  const reorder = useMutation({
    mutationFn: (trackIds: string[]) =>
      reorderPlaylistTracks(playlist.slug, trackIds),
    onSuccess: invalidate,
  });
  const duplicate = useMutation({
    mutationFn: () => duplicatePlaylist(playlist.slug),
    onSuccess: async (copy) => {
      await invalidate();
      router.push(`/playlist/${copy.slug}`);
    },
  });

  const move = (index: number, direction: -1 | 1) => {
    const target = index + direction;
    if (target < 0 || target >= playlist.tracks.length) return;
    const ids = playlist.tracks.map((track) => track.id);
    [ids[index], ids[target]] = [ids[target], ids[index]];
    reorder.mutate(ids);
  };

  return (
    <section className="rounded-2xl border border-primary/25 bg-primary/5 p-5 sm:p-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <p className="font-nepali text-xs font-semibold text-primary">
            Your playlist
          </p>
          <h2 className="mt-1 font-literary text-2xl font-semibold">
            Manage
          </h2>
        </div>
        <Button
          type="button"
          variant="ghost"
          disabled={duplicate.isPending}
          onClick={() => duplicate.mutate()}
          className="rounded-full font-nepali"
        >
          <Copy aria-hidden="true" className="size-4" />
          Duplicate
        </Button>
      </div>

      <div className="mt-5 grid gap-4 sm:grid-cols-[minmax(0,1fr)_12rem_auto] sm:items-end">
        <label className="font-nepali text-sm">
          Title
          <input
            value={title}
            minLength={2}
            maxLength={250}
            onChange={(event) => setTitle(event.target.value)}
            className="mt-2 h-11 w-full rounded-lg border border-border bg-background/60 px-3"
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
            className="mt-2 h-11 w-full rounded-lg border border-border bg-background/60 px-3"
          >
            <option value="private">Private</option>
            <option value="unlisted">Unlisted</option>
          </select>
        </label>
        <Button
          type="button"
          disabled={title.trim().length < 2 || edit.isPending}
          onClick={() => edit.mutate()}
          className="h-11 rounded-full font-nepali"
        >
          <Save aria-hidden="true" className="size-4" />
          Saved
        </Button>
      </div>

      {playlist.tracks.length ? (
        <ol className="mt-6 space-y-2">
          {playlist.tracks.map((track, index) => (
            <li
              key={track.id}
              className="flex items-center gap-3 rounded-lg border border-border bg-background/35 px-3 py-2"
            >
              <span className="w-6 text-center text-xs text-muted-foreground">
                {index + 1}
              </span>
              <span className="min-w-0 flex-1 truncate font-nepali text-sm">
                {track.title}
              </span>
              <button
                type="button"
                disabled={index === 0 || reorder.isPending}
                onClick={() => move(index, -1)}
                aria-label={`${track.title} — move up`}
                className="rounded-full p-2 disabled:opacity-30"
              >
                <ArrowUp aria-hidden="true" className="size-4" />
              </button>
              <button
                type="button"
                disabled={
                  index === playlist.tracks.length - 1 || reorder.isPending
                }
                onClick={() => move(index, 1)}
                aria-label={`${track.title} — move down`}
                className="rounded-full p-2 disabled:opacity-30"
              >
                <ArrowDown aria-hidden="true" className="size-4" />
              </button>
              <button
                type="button"
                disabled={remove.isPending}
                onClick={() => remove.mutate(track.id)}
                aria-label={`${track.title} — remove`}
                className="rounded-full p-2 text-destructive"
              >
                <X aria-hidden="true" className="size-4" />
              </button>
            </li>
          ))}
        </ol>
      ) : null}

      <div className="mt-6 flex flex-wrap items-center justify-between gap-3 border-t border-border pt-5">
        <p
          role="status"
          aria-live="polite"
          className="font-nepali text-sm text-muted-foreground"
        >
          {edit.isError || remove.isError || reorder.isError
            ? "Changes could not be saved."
            : message}
        </p>
        <Button
          type="button"
          variant="ghost"
          className="rounded-full font-nepali text-destructive"
          onClick={() => {
            if (
              window.confirm(
                "Delete this playlist permanently? This action cannot be undone.",
              )
            ) {
              void deletePlaylist(playlist.slug).then(async () => {
                await invalidate();
                router.push("/playlists");
              });
            }
          }}
        >
          <Trash2 aria-hidden="true" className="size-4" />
          Playlist — remove
        </Button>
      </div>
    </section>
  );
}
