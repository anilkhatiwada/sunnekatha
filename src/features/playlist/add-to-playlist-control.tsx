"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { ListPlus, X } from "lucide-react";
import { useState } from "react";

import { Button } from "@/components/ui/button";
import { useAuth } from "@/features/auth/auth-provider";
import {
  addTrackToPlaylist,
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
  const playlists = useQuery({
    queryKey: queryKeys.playlists.mine(),
    queryFn: getMyPlaylists,
    enabled: Boolean(user && isOpen),
  });
  const addMutation = useMutation({
    mutationFn: (slug: string) => addTrackToPlaylist(slug, trackId),
    onSuccess: async (playlist) => {
      onMessage(`“${playlist.title}” मा रचना थपियो।`);
      setIsOpen(false);
      await queryClient.invalidateQueries({
        queryKey: queryKeys.playlists.detail(playlist.slug),
      });
    },
    onError: () =>
      onMessage("प्लेलिस्टमा रचना थप्न सकिएन। फेरि प्रयास गर्नुहोस्।"),
  });

  return (
    <div className="relative">
      <Button
        type="button"
        variant="ghost"
        className="rounded-full font-nepali"
        aria-expanded={isOpen}
        onClick={() => {
          if (!user) {
            onMessage("प्लेलिस्टमा थप्न पहिले साइन इन गर्नुहोस्।");
            return;
          }
          setIsOpen((value) => !value);
        }}
      >
        <ListPlus aria-hidden="true" className="size-4" />
        प्लेलिस्टमा थप्नुहोस्
      </Button>
      {isOpen ? (
        <div className="absolute top-full left-0 z-20 mt-2 w-72 rounded-xl border border-border bg-surface p-3 shadow-2xl">
          <div className="flex items-center justify-between gap-3">
            <p className="font-nepali text-sm font-semibold">प्लेलिस्ट छान्नुहोस्</p>
            <button
              type="button"
              onClick={() => setIsOpen(false)}
              aria-label="बन्द गर्नुहोस्"
              className="rounded-full p-2 hover:bg-background"
            >
              <X aria-hidden="true" className="size-4" />
            </button>
          </div>
          <div className="mt-2 max-h-64 space-y-1 overflow-y-auto">
            {playlists.isPending ? (
              <p className="p-3 font-nepali text-sm text-muted-foreground">
                लोड हुँदैछ…
              </p>
            ) : playlists.data?.length ? (
              playlists.data.map((playlist) => (
                <button
                  key={playlist.id}
                  type="button"
                  disabled={addMutation.isPending}
                  onClick={() => addMutation.mutate(playlist.slug)}
                  className="w-full rounded-lg px-3 py-2 text-left font-nepali text-sm hover:bg-background"
                >
                  {playlist.title}
                  <span className="ml-2 text-xs text-muted-foreground">
                    {playlist.visibility === "private" ? "निजी" : ""}
                  </span>
                </button>
              ))
            ) : (
              <p className="p-3 font-nepali text-sm text-muted-foreground">
                पहिले प्लेलिस्ट बनाउनुहोस्।
              </p>
            )}
          </div>
        </div>
      ) : null}
    </div>
  );
}
