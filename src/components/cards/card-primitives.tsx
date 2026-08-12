"use client";

import { Play } from "lucide-react";
import Image from "next/image";
import Link from "next/link";
import type { ReactNode } from "react";

import { playAudioFromUserGesture } from "@/features/player/audio-engine";
import { cn } from "@/lib/utils";

interface CardPlayButtonProps {
  label: string;
  onPlay: () => void;
  className?: string;
  size?: "sm" | "md" | "lg";
  disabled?: boolean;
}

export function CardPlayButton({
  label,
  onPlay,
  className,
  size = "md",
  disabled = false,
}: CardPlayButtonProps) {
  return (
    <button
      type="button"
      aria-label={label}
      onClick={() => {
        onPlay();
        void playAudioFromUserGesture().catch(() => undefined);
      }}
      disabled={disabled}
      className={cn(
        "inline-flex shrink-0 items-center justify-center rounded-full bg-primary text-background shadow-[0_10px_28px_rgb(0_0_0_/_0.38)] transition-[transform,background-color] hover:scale-105 hover:bg-primary/90 focus-visible:scale-105 focus-visible:outline-2 focus-visible:outline-primary focus-visible:outline-offset-2 active:scale-95 disabled:pointer-events-none disabled:opacity-45",
        size === "sm" && "size-11",
        size === "md" && "size-11",
        size === "lg" && "size-14",
        className,
      )}
    >
      <Play
        aria-hidden="true"
        className={cn(
          "translate-x-px fill-current",
          size === "sm" && "size-4",
          size === "md" && "size-[1.15rem]",
          size === "lg" && "size-6",
        )}
      />
    </button>
  );
}

interface MediaArtworkProps {
  src: string;
  alt: string;
  sizes: string;
  className?: string;
  imageClassName?: string;
  priority?: boolean;
  children?: ReactNode;
}

export function MediaArtwork({
  src,
  alt,
  sizes,
  className,
  imageClassName,
  priority = false,
  children,
}: MediaArtworkProps) {
  return (
    <div
      className={cn(
        "relative isolate overflow-hidden bg-surface-soft",
        className,
      )}
    >
      <Image
        src={src}
        alt={alt}
        fill
        priority={priority}
        sizes={sizes}
        className={cn(
          "object-cover transition duration-500 group-hover:scale-[1.025]",
          imageClassName,
        )}
      />
      {children}
    </div>
  );
}

interface CardTitleLinkProps {
  href: string;
  title: string;
  className?: string;
}

export function CardTitleLink({
  href,
  title,
  className,
}: CardTitleLinkProps) {
  return (
    <Link
      href={href}
      className={cn(
        "rounded-sm font-nepali font-semibold text-foreground transition-colors hover:text-primary focus-visible:outline-2 focus-visible:outline-primary",
        className,
      )}
    >
      {title}
    </Link>
  );
}

interface PersonCardLayoutProps {
  href: string;
  image: string;
  name: string;
  description: string;
  playLabel: string;
  onPlay: () => void;
  isPlayDisabled?: boolean;
}

export function PersonCardLayout({
  href,
  image,
  name,
  description,
  playLabel,
  onPlay,
  isPlayDisabled = false,
}: PersonCardLayoutProps) {
  return (
    <article className="group min-w-0 rounded-xl border border-transparent p-3 transition-[background-color,border-color,transform] hover:-translate-y-0.5 hover:border-border/80 hover:bg-surface focus-within:border-border/80 focus-within:bg-surface">
      <MediaArtwork
        src={image}
        alt={`${name} photo`}
        sizes="(max-width: 640px) 44vw, (max-width: 1024px) 28vw, 220px"
        className="aspect-square rounded-full shadow-[0_16px_42px_rgb(0_0_0_/_0.3)]"
      >
        <div className="absolute inset-0 bg-gradient-to-t from-background/45 via-transparent to-transparent" />
        <CardPlayButton
          label={playLabel}
          onPlay={onPlay}
          disabled={isPlayDisabled}
          className="absolute right-3 bottom-3 translate-y-0 opacity-100 lg:translate-y-2 lg:opacity-0 lg:group-hover:translate-y-0 lg:group-hover:opacity-100 lg:group-focus-within:translate-y-0 lg:group-focus-within:opacity-100"
        />
      </MediaArtwork>
      <div className="mt-4 min-w-0 text-center">
        <h3 className="line-clamp-2 min-h-12">
          <CardTitleLink
            href={href}
            title={name}
            className="inline text-base leading-6"
          />
        </h3>
        <p className="mt-1 truncate font-nepali text-sm text-muted-foreground">
          {description}
        </p>
      </div>
    </article>
  );
}
