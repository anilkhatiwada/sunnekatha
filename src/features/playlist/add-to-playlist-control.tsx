"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Check, ListMusic, ListPlus, Plus, X } from "lucide-react";
import { useRef, useState } from "react";
import { createPortal } from "react-dom";

import { Button } from "@/components/ui/button";
import { useAuth } from "@/features/auth/auth-provider";
import { useModalDialog } from "@/components/player/use-modal-dialog";
import {
  addTrackToPlaylist,
  createPlaylist,
  getMyPlaylists,
  queryKeys,
} from "@/services";

export function AddToPlaylistControl({
  trackId,
  onMessage,
}: {
  trackId: string;
  onMessage: (message: string) => void;
}) {
  const { user } = useAuth();
  const queryClient = useQueryClient();
  const [isOpen, setIsOpen] = useState(false);
  const [isCreating, setIsCreating] = useState(false);
  const [newPlaylistTitle, setNewPlaylistTitle] = useState("");
  const dialogRef = useRef<HTMLElement>(null);
  const closeButtonRef = useRef<HTMLButtonElement>(null);
  const playlists = useQuery({
    queryKey: queryKeys.playlists.mine(),
    queryFn: getMyPlaylists,
    enabled: Boolean(user && isOpen),
  });

  const close = () => {
    setIsOpen(false);
    setIsCreating(false);
    setNewPlaylistTitle("");
  };

  useModalDialog({
    isOpen,
    dialogRef,
    initialFocusRef: closeButtonRef,
    onClose: close,
  });

  const finishAdding = async (playlist: { slug: string; title: string }) => {
    onMessage(`“${playlist.title}” मा रचना थपियो।`);
    close();
    await Promise.all([
      queryClient.invalidateQueries({
        queryKey: queryKeys.playlists.detail(playlist.slug),
      }),
      queryClient.invalidateQueries({
        queryKey: queryKeys.playlists.mine(),
      }),
    ]);
  };

  const addMutation = useMutation({
    mutationFn: (slug: string) => addTrackToPlaylist(slug, trackId),
    onSuccess: finishAdding,
  });
  const createMutation = useMutation({
    mutationFn: () =>
      createPlaylist({
        titleNe: newPlaylistTitle.trim(),
        visibility: "private",
      }),
    onSuccess: async (playlist) => {
      setIsCreating(false);
      setNewPlaylistTitle("");
      await queryClient.invalidateQueries({
        queryKey: queryKeys.playlists.mine(),
      });
      addMutation.mutate(playlist.slug);
    },
  });
  const isSaving = addMutation.isPending || createMutation.isPending;
  const hasError = addMutation.isError || createMutation.isError;

  return (
    <div>
      <Button
        type="button"
        variant="ghost"
        className="min-h-11 rounded-full font-nepali"
        aria-haspopup="dialog"
        aria-expanded={isOpen}
        onClick={() => {
          if (!user) {
            onMessage("प्लेलिस्टमा थप्न पहिले साइन इन गर्नुहोस्।");
            return;
          }
          addMutation.reset();
          createMutation.reset();
          setIsOpen(true);
        }}
      >
        <ListPlus aria-hidden="true" className="size-4" />
        प्लेलिस्टमा थप्नुहोस्
      </Button>

      {isOpen
        ? createPortal(
            <div data-modal-root className="fixed inset-0 z-[70]">
              <button
                type="button"
                aria-label="प्लेलिस्ट छनोट बन्द गर्नुहोस्"
                tabIndex={-1}
                onClick={close}
                className="absolute inset-0 bg-black/65 backdrop-blur-[2px]"
              />
              <section
                ref={dialogRef}
                role="dialog"
                aria-modal="true"
                aria-labelledby="playlist-picker-title"
                aria-describedby="playlist-picker-description"
                tabIndex={-1}
                className="absolute inset-x-0 bottom-0 flex max-h-[82dvh] flex-col rounded-t-2xl border border-border bg-surface shadow-2xl sm:inset-auto sm:top-1/2 sm:left-1/2 sm:max-h-[min(42rem,85dvh)] sm:w-[30rem] sm:-translate-x-1/2 sm:-translate-y-1/2 sm:rounded-2xl"
              >
                <div className="mx-auto mt-2 h-1 w-10 rounded-full bg-foreground/20 sm:hidden" />
                <header className="flex items-start justify-between gap-4 border-b border-border px-4 py-4 sm:px-5">
                  <div>
                    <h2
                      id="playlist-picker-title"
                      className="font-literary text-xl font-semibold"
                    >
                      प्लेलिस्टमा थप्नुहोस्
                    </h2>
                    <p
                      id="playlist-picker-description"
                      className="mt-1 font-nepali text-sm text-muted-foreground"
                    >
                      एउटा प्लेलिस्ट छान्नुहोस् वा नयाँ बनाउनुहोस्।
                    </p>
                  </div>
                  <Button
                    ref={closeButtonRef}
                    type="button"
                    variant="ghost"
                    size="icon"
                    onClick={close}
                    aria-label="बन्द गर्नुहोस्"
                    className="size-11 shrink-0 rounded-full"
                  >
                    <X aria-hidden="true" className="size-5" />
                  </Button>
                </header>

                <div className="min-h-0 flex-1 overflow-y-auto overscroll-contain px-3 py-3 sm:px-4">
                  {isCreating ? (
                    <form
                      onSubmit={(event) => {
                        event.preventDefault();
                        if (newPlaylistTitle.trim().length >= 2) {
                          createMutation.mutate();
                        }
                      }}
                      className="rounded-xl border border-primary/25 bg-background/45 p-4"
                    >
                      <label
                        htmlFor="new-playlist-title"
                        className="font-nepali text-sm font-semibold"
                      >
                        नयाँ निजी प्लेलिस्टको नाम
                      </label>
                      <input
                        id="new-playlist-title"
                        value={newPlaylistTitle}
                        onChange={(event) =>
                          setNewPlaylistTitle(event.target.value)
                        }
                        minLength={2}
                        maxLength={250}
                        required
                        autoFocus
                        placeholder="जस्तै: मेरा मनपर्ने कथा"
                        className="mt-2 h-12 w-full rounded-lg border border-border bg-background px-3 font-nepali text-base outline-none focus:border-primary focus:ring-2 focus:ring-primary/25"
                      />
                      <div className="mt-3 flex gap-2">
                        <Button
                          type="submit"
                          disabled={
                            newPlaylistTitle.trim().length < 2 || isSaving
                          }
                          className="min-h-11 flex-1 rounded-full font-nepali"
                        >
                          <Check aria-hidden="true" className="size-4" />
                          {createMutation.isPending
                            ? "बनाउँदै र थप्दै…"
                            : "बनाएर थप्नुहोस्"}
                        </Button>
                        <Button
                          type="button"
                          variant="ghost"
                          disabled={isSaving}
                          onClick={() => {
                            setIsCreating(false);
                            setNewPlaylistTitle("");
                          }}
                          className="min-h-11 rounded-full font-nepali"
                        >
                          रद्द
                        </Button>
                      </div>
                    </form>
                  ) : (
                    <Button
                      type="button"
                      variant="secondary"
                      disabled={isSaving}
                      onClick={() => setIsCreating(true)}
                      className="min-h-12 w-full justify-start rounded-xl font-nepali"
                    >
                      <Plus aria-hidden="true" className="size-5 text-primary" />
                      नयाँ प्लेलिस्ट बनाएर थप्नुहोस्
                    </Button>
                  )}

                  <div className="my-3 h-px bg-border" />
                  {playlists.isPending ? (
                    <p className="p-4 font-nepali text-sm text-muted-foreground">
                      तपाईंका प्लेलिस्ट लोड हुँदैछन्…
                    </p>
                  ) : playlists.isError ? (
                    <div role="alert" className="p-3">
                      <p className="font-nepali text-sm text-destructive">
                        प्लेलिस्ट लोड गर्न सकिएन।
                      </p>
                      <Button
                        type="button"
                        variant="ghost"
                        onClick={() => void playlists.refetch()}
                        className="mt-2 min-h-11 rounded-full font-nepali"
                      >
                        फेरि प्रयास गर्नुहोस्
                      </Button>
                    </div>
                  ) : playlists.data?.length ? (
                    <div className="space-y-1" aria-label="तपाईंका प्लेलिस्ट">
                      {playlists.data.map((playlist) => (
                        <button
                          key={playlist.id}
                          type="button"
                          disabled={isSaving}
                          onClick={() => addMutation.mutate(playlist.slug)}
                          className="flex min-h-14 w-full items-center gap-3 rounded-xl px-3 py-2.5 text-left transition-colors hover:bg-background focus-visible:outline-2 focus-visible:outline-primary disabled:opacity-60"
                        >
                          <span className="grid size-10 shrink-0 place-items-center rounded-lg bg-primary-muted/30 text-primary">
                            <ListMusic aria-hidden="true" className="size-5" />
                          </span>
                          <span className="min-w-0 flex-1">
                            <span className="block truncate font-nepali text-sm font-semibold">
                              {playlist.title}
                            </span>
                            <span className="block font-nepali text-xs text-muted-foreground">
                              {playlist.trackCount} रचना
                              {playlist.visibility === "private"
                                ? " · निजी"
                                : ""}
                            </span>
                          </span>
                          {addMutation.isPending &&
                          addMutation.variables === playlist.slug ? (
                            <span className="font-nepali text-xs text-primary">
                              थप्दै…
                            </span>
                          ) : null}
                        </button>
                      ))}
                    </div>
                  ) : (
                    <div className="px-3 py-6 text-center">
                      <ListMusic
                        aria-hidden="true"
                        className="mx-auto size-8 text-muted-foreground"
                      />
                      <p className="mt-2 font-nepali text-sm text-muted-foreground">
                        तपाईंको प्लेलिस्ट अझै छैन। माथिबाट नयाँ बनाउनुहोस्।
                      </p>
                    </div>
                  )}

                  {hasError ? (
                    <p
                      role="alert"
                      className="mt-3 rounded-lg bg-destructive/10 px-3 py-2 font-nepali text-sm text-destructive"
                    >
                      रचना थप्न सकिएन। यो रचना पहिल्यै हुन सक्छ वा फेरि प्रयास
                      गर्नुपर्छ।
                    </p>
                  ) : null}
                </div>
                <div className="h-[env(safe-area-inset-bottom)] shrink-0 sm:hidden" />
              </section>
            </div>,
            document.body,
          )
        : null}
    </div>
  );
}
