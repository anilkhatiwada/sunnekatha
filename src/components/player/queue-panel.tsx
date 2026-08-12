"use client";

import {
  GripVertical,
  Headphones,
  ListMusic,
  Play,
  Trash2,
  X,
} from "lucide-react";
import Image from "next/image";
import { useRef, useState } from "react";
import { createPortal } from "react-dom";

import { Button } from "@/components/ui/button";
import { EmptyState } from "@/components/common/empty-state";
import { useModalDialog } from "@/components/player/use-modal-dialog";
import { usePlayerStore } from "@/features/player/player-store";
import { formatPlayerTime } from "@/lib/formatters";
import { cn } from "@/lib/utils";
import type { QueueItem } from "@/types";

interface QueuePanelProps {
  isOpen: boolean;
  onClose: () => void;
}

export function QueuePanel({ isOpen, onClose }: QueuePanelProps) {
  const queue = usePlayerStore((state) => state.queue);
  const currentQueueIndex = usePlayerStore(
    (state) => state.currentQueueIndex,
  );
  const playQueueItem = usePlayerStore((state) => state.playQueueItem);
  const moveQueueItem = usePlayerStore((state) => state.moveQueueItem);
  const removeFromQueue = usePlayerStore((state) => state.removeFromQueue);
  const clearQueue = usePlayerStore((state) => state.clearQueue);
  const [draggedItemId, setDraggedItemId] = useState<string | null>(null);
  const dialogRef = useRef<HTMLElement>(null);
  const closeButtonRef = useRef<HTMLButtonElement>(null);
  const nowPlaying = queue[currentQueueIndex];
  const upNext = queue.slice(Math.max(currentQueueIndex + 1, 0));

  useModalDialog({
    isOpen,
    dialogRef,
    initialFocusRef: closeButtonRef,
    onClose,
  });

  if (!isOpen) return null;

  return createPortal(
    <div data-modal-root className="fixed inset-0 z-[65]">
      <button
        type="button"
        aria-label="Close queue"
        tabIndex={-1}
        onClick={onClose}
        className="absolute inset-0 bg-black/55 backdrop-blur-[2px]"
      />
      <aside
        ref={dialogRef}
        role="dialog"
        aria-modal="true"
        aria-labelledby="queue-panel-title"
        aria-describedby="queue-panel-description"
        tabIndex={-1}
        className="absolute inset-x-0 bottom-0 flex max-h-[85dvh] flex-col rounded-t-2xl border border-border bg-surface/98 pb-[env(safe-area-inset-bottom)] shadow-2xl lg:inset-y-0 lg:right-0 lg:left-auto lg:max-h-none lg:w-[26rem] lg:rounded-none lg:rounded-l-2xl lg:pb-0"
      >
        <div className="mx-auto mt-2 h-1 w-10 rounded-full bg-foreground/20 lg:hidden" />
        <header className="flex items-center justify-between border-b border-border px-4 py-3 sm:px-5">
          <div>
            <h2
              id="queue-panel-title"
              className="font-literary text-xl font-semibold"
            >
              Queue
            </h2>
            <p
              id="queue-panel-description"
              className="font-nepali text-xs text-muted-foreground"
            >
              {queue.length} tracks
            </p>
          </div>
          <div className="flex items-center gap-1">
            <Button
              type="button"
              variant="ghost"
              size="sm"
              disabled={queue.length === 0}
              onClick={clearQueue}
              className="min-h-11 font-nepali text-xs text-muted-foreground hover:text-destructive"
            >
              Clear all
            </Button>
            <Button
              ref={closeButtonRef}
              type="button"
              variant="ghost"
              size="icon"
              onClick={onClose}
              aria-label="Close queue"
              className="size-11 rounded-full"
            >
              <X aria-hidden="true" className="size-5" />
            </Button>
          </div>
        </header>

        {queue.length === 0 ? (
          <div className="flex-1 px-4 py-8">
            <EmptyState
              icon={ListMusic}
              title="Your queue is empty"
              description="Upcoming tracks will appear here when you play a story, poem, or playlist."
              className="h-full border-0 bg-transparent"
            />
          </div>
        ) : (
          <div className="min-h-0 flex-1 overflow-y-auto px-3 py-4 sm:px-4">
            {nowPlaying ? (
              <section aria-labelledby="now-playing-heading">
                <h3
                  id="now-playing-heading"
                  className="mb-2 px-1 font-nepali text-xs font-semibold tracking-wide text-primary"
                >
                  Now playing
                </h3>
                <QueueTrack
                  item={nowPlaying}
                  isActive
                  onPlay={() => playQueueItem(nowPlaying.id)}
                  onRemove={() => removeFromQueue(nowPlaying.id)}
                />
              </section>
            ) : null}

            <section
              aria-labelledby="up-next-heading"
              className={cn(nowPlaying && "mt-6")}
            >
              <h3
                id="up-next-heading"
                className="mb-2 px-1 font-nepali text-xs font-semibold tracking-wide text-muted-foreground"
              >
                Up next
              </h3>
              {upNext.length > 0 ? (
                <ol className="space-y-1">
                  {upNext.map((item, upNextIndex) => {
                    const queueIndex =
                      Math.max(currentQueueIndex + 1, 0) + upNextIndex;

                    return (
                      <li
                        key={item.id}
                        draggable
                        onDragStart={() => setDraggedItemId(item.id)}
                        onDragEnd={() => setDraggedItemId(null)}
                        onDragOver={(event) => event.preventDefault()}
                        onDrop={() => {
                          if (draggedItemId) {
                            moveQueueItem(draggedItemId, queueIndex);
                          }
                          setDraggedItemId(null);
                        }}
                        className={cn(
                          "rounded-lg transition-opacity",
                          draggedItemId === item.id && "opacity-45",
                        )}
                      >
                        <QueueTrack
                          item={item}
                          onPlay={() => playQueueItem(item.id)}
                          onRemove={() => removeFromQueue(item.id)}
                          dragHandle={
                            <Button
                              type="button"
                              variant="ghost"
                              size="icon"
                              aria-label={`${item.track.title} — change position`}
                              title="Drag or use the up and down arrow keys"
                              onKeyDown={(event) => {
                                if (event.key === "ArrowUp") {
                                  event.preventDefault();
                                  moveQueueItem(
                                    item.id,
                                    Math.max(
                                      currentQueueIndex + 1,
                                      queueIndex - 1,
                                    ),
                                  );
                                }
                                if (event.key === "ArrowDown") {
                                  event.preventDefault();
                                  moveQueueItem(item.id, queueIndex + 1);
                                }
                              }}
                              className="size-11 shrink-0 cursor-grab text-muted-foreground active:cursor-grabbing"
                            >
                              <GripVertical
                                aria-hidden="true"
                                className="size-4"
                              />
                            </Button>
                          }
                        />
                      </li>
                    );
                  })}
                </ol>
              ) : (
                <p className="rounded-lg border border-dashed border-border px-4 py-6 text-center font-nepali text-sm text-muted-foreground">
                  Nothing else is queued
                </p>
              )}
            </section>
          </div>
        )}
      </aside>
    </div>,
    document.body,
  );
}

interface QueueTrackProps {
  item: QueueItem;
  isActive?: boolean;
  onPlay: () => void;
  onRemove: () => void;
  dragHandle?: React.ReactNode;
}

function QueueTrack({
  item,
  isActive = false,
  onPlay,
  onRemove,
  dragHandle,
}: QueueTrackProps) {
  return (
    <div
      aria-current={isActive ? "true" : undefined}
      className={cn(
        "group flex items-center gap-2 rounded-lg p-2 transition-colors hover:bg-surface-soft",
        isActive && "bg-primary-muted/35 ring-1 ring-primary/20",
      )}
    >
      {dragHandle}
      <Image
        src={item.track.coverImage}
        alt={`${item.track.title} cover`}
        width={48}
        height={48}
        className="size-11 shrink-0 rounded-md object-cover sm:size-12"
      />
      <button
        type="button"
        onClick={onPlay}
        className="min-h-11 min-w-0 flex-1 rounded-md text-left focus-visible:outline-2 focus-visible:outline-primary"
        aria-label={`${item.track.title} — play`}
      >
        <span className="block truncate font-nepali text-sm font-medium text-foreground">
          {item.track.title}
        </span>
        <span className="block truncate font-nepali text-xs text-muted-foreground">
          {item.track.author.name} · {item.track.narrator.name}
        </span>
      </button>
      <span className="hidden shrink-0 text-[0.7rem] tabular-nums text-muted-foreground sm:inline">
        {formatPlayerTime(item.track.duration)}
      </span>
      <Button
        type="button"
        variant="ghost"
        size="icon"
        onClick={onRemove}
        aria-label={`${item.track.title} — remove from queue`}
        className="size-11 shrink-0 rounded-full text-muted-foreground hover:text-destructive"
      >
        <Trash2 aria-hidden="true" className="size-4" />
      </Button>
      {isActive ? (
        <Headphones
          aria-label="Now playing"
          className="hidden size-4 shrink-0 text-primary sm:block"
        />
      ) : (
        <Play
          aria-hidden="true"
          className="hidden size-3 shrink-0 fill-current text-primary group-hover:block"
        />
      )}
    </div>
  );
}
