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
  const [visibility, setVisibility] = useState<
    "private" | "unlisted" | "public"
  >("private");
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
        message="प्लेलिस्टहरू लोड गर्न सकिएन। कृपया फेरि प्रयास गर्नुहोस्।"
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
              सुन्नका लागि तयार सङ्ग्रह
            </p>
            <h1 className="mt-2 font-literary text-4xl font-semibold sm:text-5xl">
              प्लेलिस्ट
            </h1>
            <p className="mt-3 max-w-2xl font-nepali text-sm leading-7 text-muted-foreground">
              सम्पादकले छानेका र आफ्नै रुचिअनुसार बनाएका रचनाहरू एउटै ठाउँमा।
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
              {isCreating ? "बन्द गर्नुहोस्" : "नयाँ प्लेलिस्ट"}
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
            नयाँ प्लेलिस्ट
          </h2>
          <div className="mt-5 grid gap-4 sm:grid-cols-[minmax(0,1fr)_12rem_auto] sm:items-end">
            <label className="font-nepali text-sm">
              शीर्षक
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
              दृश्यता
              <select
                value={visibility}
                onChange={(event) =>
                  setVisibility(
                    event.target.value as
                      | "private"
                      | "unlisted"
                      | "public",
                  )
                }
                className={`${inputClassName} mt-2`}
              >
                <option value="private">निजी</option>
                <option value="unlisted">लिङ्क भएका मात्र</option>
                <option value="public">सार्वजनिक</option>
              </select>
            </label>
            <Button
              type="submit"
              disabled={title.trim().length < 2 || createMutation.isPending}
              className="h-11 rounded-full font-nepali"
            >
              {createMutation.isPending ? "बनाउँदै…" : "बनाउनुहोस्"}
            </Button>
          </div>
          {createMutation.isError ? (
            <p role="alert" className="mt-3 font-nepali text-sm text-destructive">
              प्लेलिस्ट बनाउन सकिएन। शीर्षक र अनुमति जाँच गरी फेरि प्रयास
              गर्नुहोस्।
            </p>
          ) : null}
        </form>
      ) : null}

      {user ? (
        <PlaylistGrid
          title="मेरा प्लेलिस्ट"
          eyebrow="व्यक्तिगत सङ्ग्रह"
          isPending={mineQuery.isPending}
          playlists={mineQuery.data ?? []}
          emptyDescription="पहिलो प्लेलिस्ट बनाएर मनपर्ने रचना थप्नुहोस्।"
          onPlay={(playlist) => void playPlaylist(playlist)}
        />
      ) : (
        <section className="rounded-2xl border border-dashed border-border bg-surface/40 p-6">
          <h2 className="font-literary text-2xl font-semibold">
            आफ्नै प्लेलिस्ट बनाउनुहोस्
          </h2>
          <p className="mt-2 font-nepali text-sm text-muted-foreground">
            निजी सङ्ग्रह बनाउन र उपकरणहरूबीच सुरक्षित राख्न साइन इन गर्नुहोस्।
          </p>
          <Button
            type="button"
            onClick={() => window.location.assign("/login")}
            className="mt-5 rounded-full font-nepali"
          >
            साइन इन गर्नुहोस्
          </Button>
        </section>
      )}

      <PlaylistGrid
        title="सार्वजनिक प्लेलिस्ट"
        eyebrow="सम्पादकीय र समुदाय"
        isPending={publicQuery.isPending}
        playlists={publicQuery.data ?? []}
        emptyDescription="सार्वजनिक प्लेलिस्ट तयार भएपछि यहाँ देखिनेछन्।"
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
          title="अहिलेसम्म खाली छ"
          description={emptyDescription}
          className="mt-5"
        />
      )}
    </section>
  );
}
