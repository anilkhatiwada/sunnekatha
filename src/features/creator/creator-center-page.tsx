"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { FileAudio, Send, UploadCloud } from "lucide-react";
import Link from "next/link";

import { EmptyState } from "@/components/common/empty-state";
import { ErrorState } from "@/components/common/error-state";
import { LoadingSkeleton } from "@/components/common/loading-skeleton";
import { Button } from "@/components/ui/button";
import { useAuth } from "@/features/auth/auth-provider";
import {
  getCreatorDrafts,
  getCreatorProfile,
  getCreatorUploads,
  queryKeys,
  submitCreatorTrack,
} from "@/services";
import { unwrapPage } from "@/services/public-api-utils";

export function CreatorCenterPage() {
  const { user } = useAuth();
  const queryClient = useQueryClient();
  const profile = useQuery({
    queryKey: queryKeys.creator.profile(),
    queryFn: getCreatorProfile,
    enabled: Boolean(user?.isCreator),
  });
  const drafts = useQuery({
    queryKey: queryKeys.creator.drafts(),
    queryFn: getCreatorDrafts,
    enabled: Boolean(user?.isCreator),
  });
  const uploads = useQuery({
    queryKey: queryKeys.creator.uploads(),
    queryFn: getCreatorUploads,
    enabled: Boolean(user?.isCreator),
  });
  const submit = useMutation({
    mutationFn: submitCreatorTrack,
    onSuccess: () =>
      queryClient.invalidateQueries({ queryKey: queryKeys.creator.drafts() }),
  });

  if (!user?.isCreator) {
    return (
      <EmptyState
        icon={FileAudio}
        title="Creator access required"
        description="This area is for approved creators and editorial staff."
      />
    );
  }
  if (profile.isError || drafts.isError || uploads.isError) {
    return (
      <ErrorState
        message="Creator Center could not be loaded."
        onRetry={() => {
          void profile.refetch();
          void drafts.refetch();
          void uploads.refetch();
        }}
      />
    );
  }

  const draftItems = drafts.data ? unwrapPage(drafts.data) : [];
  const uploadItems = uploads.data ? unwrapPage(uploads.data) : [];

  return (
    <div className="space-y-10 pb-8">
      <header className="flex flex-wrap items-end justify-between gap-5 rounded-2xl border border-border bg-surface/70 p-6 sm:p-8">
        <div>
          <p className="font-nepali text-sm font-semibold text-primary">
            Creator Center
          </p>
          <h1 className="mt-2 font-literary text-4xl font-semibold">
            {profile.data?.displayName ?? user.displayName}
          </h1>
          <p className="mt-2 font-nepali text-sm text-muted-foreground">
            {profile.data?.isApproved ? "Approved creator" : "Awaiting approval"}
          </p>
        </div>
        <Link
          href="/creator/uploads"
          className="inline-flex min-h-11 items-center gap-2 rounded-full bg-primary px-5 py-2 font-nepali text-sm font-semibold text-background"
        >
          <UploadCloud aria-hidden="true" className="size-4" />
          Upload new file
        </Link>
      </header>

      <section>
        <h2 className="font-literary text-3xl font-semibold">Draft tracks</h2>
        {drafts.isPending ? (
          <LoadingSkeleton className="mt-4 h-32 rounded-xl" />
        ) : draftItems.length ? (
          <div className="mt-4 space-y-2">
            {draftItems.map((track) => (
              <article
                key={track.id}
                className="flex flex-wrap items-center gap-4 rounded-xl border border-border bg-surface/55 p-4"
              >
                <div className="min-w-0 flex-1">
                  <Link
                    href={`/track/${track.slug}`}
                    className="font-nepali font-semibold hover:text-primary"
                  >
                    {track.title}
                  </Link>
                  <p className="mt-1 font-nepali text-xs text-muted-foreground">
                    Processing: {track.processingStatus} · Review:{" "}
                    {track.reviewStatus}
                  </p>
                </div>
                <Button
                  type="button"
                  variant="secondary"
                  disabled={
                    submit.isPending ||
                    !["draft", "rejected", "changes_requested"].includes(
                      track.reviewStatus,
                    )
                  }
                  onClick={() => submit.mutate(track.slug)}
                  className="rounded-full font-nepali"
                >
                  <Send aria-hidden="true" className="size-4" />
                  Submit for review
                </Button>
              </article>
            ))}
          </div>
        ) : (
          <EmptyState
            compact
            icon={FileAudio}
            title="No drafts"
            description="Tracks will appear here after the editorial team links an upload."
            className="mt-4"
          />
        )}
        {submit.isError ? (
          <p role="alert" className="mt-3 font-nepali text-sm text-destructive">
            The track could not be submitted. Check required metadata, rights, and audio status.
          </p>
        ) : null}
      </section>

      <section>
        <h2 className="font-literary text-3xl font-semibold">Recent uploads</h2>
        {uploads.isPending ? (
          <LoadingSkeleton className="mt-4 h-28 rounded-xl" />
        ) : uploadItems.length ? (
          <ul className="mt-4 divide-y divide-border rounded-xl border border-border bg-surface/55">
            {uploadItems.slice(0, 10).map((upload) => (
              <li
                key={upload.id}
                className="flex items-center justify-between gap-4 px-4 py-3"
              >
                <span className="min-w-0 truncate font-nepali text-sm">
                  {upload.originalFilename}
                </span>
                <span className="shrink-0 font-nepali text-xs text-muted-foreground">
                  {upload.status}
                </span>
              </li>
            ))}
          </ul>
        ) : (
          <p className="mt-4 font-nepali text-sm text-muted-foreground">
            No uploads yet.
          </p>
        )}
      </section>
    </div>
  );
}
