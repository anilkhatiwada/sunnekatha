"use client";

import {
  ChevronDown,
  Download,
  Gauge,
  Heart,
  ListMusic,
  Share2,
  Timer,
} from "lucide-react";
import Image from "next/image";
import { useEffect, useRef, useState } from "react";
import { createPortal } from "react-dom";

import { PlayerControls } from "@/components/player/player-controls";
import { PlayerProgress } from "@/components/player/player-progress";
import { useModalDialog } from "@/components/player/use-modal-dialog";
import { Button } from "@/components/ui/button";
import { usePlayerStore } from "@/features/player/player-store";
import { cn } from "@/lib/utils";
import { sharePage } from "@/lib/share";
import type { Track } from "@/types";

interface FullPlayerPanelProps {
  track: Track;
  isFavorite: boolean;
  onClose: () => void;
  onToggleFavorite: () => void;
  onOpenQueue: () => void;
}

type DetailTab = "transcript" | "description";

const PLAYBACK_SPEEDS = [0.75, 1, 1.25, 1.5, 2] as const;

export function FullPlayerPanel({
  track,
  isFavorite,
  onClose,
  onToggleFavorite,
  onOpenQueue,
}: FullPlayerPanelProps) {
  const playbackSpeed = usePlayerStore((state) => state.playbackSpeed);
  const setPlaybackSpeed = usePlayerStore(
    (state) => state.setPlaybackSpeed,
  );
  const [activeTab, setActiveTab] = useState<DetailTab>("transcript");
  const [placeholderNotice, setPlaceholderNotice] = useState<string | null>(
    null,
  );
  const [sleepMinutes, setSleepMinutes] = useState(0);
  const pause = usePlayerStore((state) => state.pause);
  const dialogRef = useRef<HTMLDivElement>(null);
  const closeButtonRef = useRef<HTMLButtonElement>(null);

  useModalDialog({
    isOpen: true,
    dialogRef,
    initialFocusRef: closeButtonRef,
    onClose,
  });

  const cyclePlaybackSpeed = () => {
    const currentIndex = PLAYBACK_SPEEDS.findIndex(
      (speed) => speed === playbackSpeed,
    );
    const nextIndex =
      currentIndex < 0 || currentIndex === PLAYBACK_SPEEDS.length - 1
        ? 0
        : currentIndex + 1;
    setPlaybackSpeed(PLAYBACK_SPEEDS[nextIndex]);
  };

  useEffect(() => {
    if (!sleepMinutes) return;
    const timeout = window.setTimeout(() => {
      pause();
      setSleepMinutes(0);
      setPlaceholderNotice("निद्रा टाइमर पूरा भयो। प्लेब्याक रोकियो।");
    }, sleepMinutes * 60_000);
    return () => window.clearTimeout(timeout);
  }, [pause, sleepMinutes]);

  const showPlaceholderNotice = (label: string) => {
    setPlaceholderNotice(`${label} सुविधा चाँडै उपलब्ध हुनेछ।`);
  };
  const selectTabFromKeyboard = (
    event: React.KeyboardEvent<HTMLButtonElement>,
    currentTab: DetailTab,
  ) => {
    const currentIndex = currentTab === "transcript" ? 0 : 1;
    let nextTab: DetailTab | null = null;

    if (event.key === "ArrowRight" || event.key === "ArrowLeft") {
      const direction = event.key === "ArrowRight" ? 1 : -1;
      nextTab = (["transcript", "description"] as const)[
        (currentIndex + direction + 2) % 2
      ];
    } else if (event.key === "Home") {
      nextTab = "transcript";
    } else if (event.key === "End") {
      nextTab = "description";
    }

    if (!nextTab) return;

    event.preventDefault();
    setActiveTab(nextTab);
    document.getElementById(`${nextTab}-tab`)?.focus();
  };

  return createPortal(
    <div
      data-modal-root
      ref={dialogRef}
      role="dialog"
      aria-modal="true"
      aria-labelledby="full-player-title"
      aria-describedby="full-player-description"
      tabIndex={-1}
      className="fixed inset-0 z-[70] overflow-y-auto bg-background/98 backdrop-blur-2xl"
    >
      <div className="pointer-events-none fixed inset-0 bg-[radial-gradient(circle_at_50%_12%,rgb(111_63_43_/_0.34),transparent_42rem)]" />
      <div className="relative mx-auto flex min-h-dvh max-w-6xl flex-col px-5 pt-[max(1rem,env(safe-area-inset-top))] pb-[max(1.5rem,env(safe-area-inset-bottom))] sm:px-8 lg:px-12">
        <header className="flex items-center justify-between">
          <Button
            ref={closeButtonRef}
            type="button"
            variant="ghost"
            size="icon"
            onClick={onClose}
            aria-label="पूर्ण प्लेयर बन्द गर्नुहोस्"
            className="rounded-full bg-surface/45 backdrop-blur-md"
          >
            <ChevronDown aria-hidden="true" className="size-6" />
          </Button>
          <div className="text-center">
            <p className="font-nepali text-xs font-medium tracking-wide text-primary">
              अहिले बज्दैछ
            </p>
            <p className="mt-0.5 hidden font-nepali text-xs text-muted-foreground sm:block">
              SunneKatha
            </p>
          </div>
          <Button
            type="button"
            variant="ghost"
            size="icon"
            onClick={onToggleFavorite}
            aria-label={
              isFavorite ? "मनपर्नेबाट हटाउनुहोस्" : "मनपर्नेमा राख्नुहोस्"
            }
            aria-pressed={isFavorite}
            className={cn(
              "rounded-full bg-surface/45 backdrop-blur-md",
              isFavorite && "text-primary",
            )}
          >
            <Heart
              aria-hidden="true"
              className={cn("size-5", isFavorite && "fill-current")}
            />
          </Button>
        </header>

        <div className="grid flex-1 items-center gap-8 py-8 lg:grid-cols-[minmax(20rem,0.9fr)_minmax(24rem,1.1fr)] lg:gap-14 lg:py-10">
          <div className="mx-auto w-full max-w-[28rem] lg:max-w-none">
            <Image
              src={track.coverImage}
              alt={`${track.title} को आवरण`}
              width={800}
              height={800}
              className="aspect-square w-full rounded-2xl object-cover shadow-[0_32px_100px_rgb(0_0_0_/_0.58)] ring-1 ring-white/10"
            />
          </div>

          <div className="mx-auto w-full max-w-2xl">
            <div className="min-w-0">
              <h2
                id="full-player-title"
                className="font-literary text-3xl leading-tight font-semibold text-foreground sm:text-4xl"
              >
                {track.title}
              </h2>
              <div
                id="full-player-description"
                className="mt-3 grid gap-1 font-nepali text-sm sm:grid-cols-2"
              >
                <p className="text-muted-foreground">
                  लेखक{" "}
                  <span className="text-foreground">{track.author.name}</span>
                </p>
                <p className="text-muted-foreground sm:text-right">
                  वाचक{" "}
                  <span className="text-foreground">
                    {track.narrator.name}
                  </span>
                </p>
              </div>
            </div>

            <PlayerProgress className="mt-7" />
            <PlayerControls className="mt-5 gap-3 [&_button]:size-11 [&_button:nth-child(3)]:size-14" />

            <div className="mt-6 grid grid-cols-5 gap-1 rounded-xl border border-border/80 bg-surface/55 p-2 backdrop-blur-md">
              <UtilityButton
                icon={Download}
                label="डाउनलोड"
                onClick={() => showPlaceholderNotice("डाउनलोड")}
              />
              <UtilityButton
                icon={Share2}
                label="साझा"
                onClick={() => {
                  void sharePage({
                    title: track.title,
                    text: `${track.title} · SunneKatha`,
                    url: `${window.location.origin}/track/${track.slug}`,
                  })
                    .then((result) =>
                      setPlaceholderNotice(
                        result === "copied"
                          ? "रचनाको लिङ्क प्रतिलिपि भयो।"
                          : "रचना साझा भयो।",
                      ),
                    )
                    .catch(() => undefined);
                }}
              />
              <UtilityButton
                icon={ListMusic}
                label="प्ले सूची"
                onClick={onOpenQueue}
              />
              <UtilityButton
                icon={Gauge}
                label={`${playbackSpeed}×`}
                onClick={cyclePlaybackSpeed}
                ariaLabel={`प्लेब्याक गति ${playbackSpeed} गुणा। परिवर्तन गर्नुहोस्`}
              />
              <UtilityButton
                icon={Timer}
                label={sleepMinutes ? `${sleepMinutes} मिनेट` : "निद्रा टाइमर"}
                onClick={() => {
                  const next =
                    sleepMinutes === 0
                      ? 15
                      : sleepMinutes === 15
                        ? 30
                        : sleepMinutes === 30
                          ? 45
                          : 0;
                  setSleepMinutes(next);
                  setPlaceholderNotice(
                    next
                      ? `निद्रा टाइमर ${next} मिनेटमा सेट भयो।`
                      : "निद्रा टाइमर बन्द भयो।",
                  );
                }}
              />
            </div>

            <p
              role="status"
              aria-live="polite"
              className="mt-2 min-h-5 text-center font-nepali text-xs text-muted-foreground"
            >
              {placeholderNotice}
            </p>

            <div className="mt-5 overflow-hidden rounded-xl border border-border/80 bg-surface/45 backdrop-blur-md">
              <div
                role="tablist"
                aria-label="ट्र्याक विवरण"
                className="grid grid-cols-2 border-b border-border"
              >
                <DetailTabButton
                  id="transcript"
                  label="पाठ"
                  isActive={activeTab === "transcript"}
                  onSelect={setActiveTab}
                  onKeyDown={selectTabFromKeyboard}
                />
                <DetailTabButton
                  id="description"
                  label="विवरण"
                  isActive={activeTab === "description"}
                  onSelect={setActiveTab}
                  onKeyDown={selectTabFromKeyboard}
                />
              </div>
              <div
                role="tabpanel"
                id={`${activeTab}-panel`}
                aria-labelledby={`${activeTab}-tab`}
                tabIndex={0}
                className="max-h-48 overflow-y-auto px-5 py-4 focus-visible:outline-2 focus-visible:outline-primary"
              >
                {activeTab === "transcript" ? (
                  track.transcript ? (
                    <p className="whitespace-pre-line font-literary text-lg leading-9 text-foreground/90">
                      {track.transcript}
                    </p>
                  ) : (
                    <div className="py-3 text-center">
                      <p className="font-nepali text-sm text-foreground">
                        यस रचनाको पाठ तयार हुँदैछ
                      </p>
                      <p className="mt-1 font-nepali text-xs leading-5 text-muted-foreground">
                        समयसँग मिल्ने साहित्यिक पाठ भविष्यको संस्करणमा यहाँ
                        देखिनेछ।
                      </p>
                    </div>
                  )
                ) : (
                  <p className="font-nepali text-sm leading-7 text-foreground/85">
                    {track.description ??
                      "यस रचनाको विस्तृत विवरण चाँडै उपलब्ध हुनेछ।"}
                  </p>
                )}
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>,
    document.body,
  );
}

interface UtilityButtonProps {
  icon: React.ComponentType<{ className?: string; "aria-hidden"?: boolean }>;
  label: string;
  ariaLabel?: string;
  onClick: () => void;
}

function UtilityButton({
  icon: Icon,
  label,
  ariaLabel,
  onClick,
}: UtilityButtonProps) {
  return (
    <button
      type="button"
      onClick={onClick}
      aria-label={ariaLabel ?? label}
      className="flex min-w-0 flex-col items-center gap-1.5 rounded-lg px-1 py-2 font-nepali text-[0.65rem] text-muted-foreground transition-colors hover:bg-surface-soft hover:text-foreground focus-visible:outline-2 focus-visible:outline-primary sm:text-xs"
    >
      <Icon aria-hidden={true} className="size-4.5" />
      <span className="max-w-full truncate">{label}</span>
    </button>
  );
}

interface DetailTabButtonProps {
  id: DetailTab;
  label: string;
  isActive: boolean;
  onSelect: (tab: DetailTab) => void;
  onKeyDown: (
    event: React.KeyboardEvent<HTMLButtonElement>,
    tab: DetailTab,
  ) => void;
}

function DetailTabButton({
  id,
  label,
  isActive,
  onSelect,
  onKeyDown,
}: DetailTabButtonProps) {
  return (
    <button
      type="button"
      role="tab"
      id={`${id}-tab`}
      aria-controls={`${id}-panel`}
      aria-selected={isActive}
      tabIndex={isActive ? 0 : -1}
      onClick={() => onSelect(id)}
      onKeyDown={(event) => onKeyDown(event, id)}
      className={cn(
        "border-b-2 px-4 py-3 font-nepali text-sm transition-colors focus-visible:outline-2 focus-visible:outline-primary",
        isActive
          ? "border-primary text-foreground"
          : "border-transparent text-muted-foreground hover:text-foreground",
      )}
    >
      {label}
    </button>
  );
}
