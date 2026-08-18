import type { Metadata } from "next";

import { environment } from "@/config/environment";
import type { ApiDetailedTrack } from "@/types/backend-api";

export const SOCIAL_IMAGE_PATH = "/brand/sunnekatha-og.jpg";
export const SOCIAL_IMAGE = {
  url: SOCIAL_IMAGE_PATH,
  width: 1200,
  height: 630,
  alt: "SunneKatha — Nepali audio literature",
};
const SOCIAL_DESCRIPTION_LIMIT = 180;

export async function getSocialTrack(slug: string) {
  try {
    const response = await fetch(
      `${environment.apiBaseUrl}/tracks/${encodeURIComponent(slug)}/`,
      {
        headers: { Accept: "application/json" },
        next: { revalidate: 300 },
      },
    );
    if (!response.ok) return null;

    const value: unknown = await response.json();
    return isSocialTrack(value) ? value : null;
  } catch {
    return null;
  }
}

export function buildTrackMetadata(
  slug: string,
  track: ApiDetailedTrack | null,
): Metadata {
  const canonicalPath = `/track/${encodeURIComponent(slug)}`;
  if (!track) {
    return {
      title: "Track",
      description: "Listen to Nepali audio literature on SunneKatha.",
      alternates: { canonical: canonicalPath },
      openGraph: {
        type: "website",
        url: canonicalPath,
        siteName: "SunneKatha",
        locale: "ne_NP",
        title: "Track",
        description: "Listen to Nepali audio literature on SunneKatha.",
        images: [SOCIAL_IMAGE],
      },
      twitter: {
        card: "summary_large_image",
        title: "Track",
        description: "Listen to Nepali audio literature on SunneKatha.",
        images: [SOCIAL_IMAGE_PATH],
      },
    };
  }

  const creator = track.author.name;
  const category = track.category?.name || track.literaryWork.category?.name;
  const fallbackDescription = [creator, category, "Listen on SunneKatha"]
    .filter(Boolean)
    .join(" · ");
  const description = truncateDescription(
    track.description || track.descriptionEnglish || fallbackDescription,
  );

  return {
    title: track.title,
    description,
    alternates: { canonical: canonicalPath },
    openGraph: {
      type: "website",
      url: canonicalPath,
      siteName: "SunneKatha",
      locale: "ne_NP",
      title: track.title,
      description,
      images: [SOCIAL_IMAGE],
    },
    twitter: {
      card: "summary_large_image",
      title: track.title,
      description,
      images: [SOCIAL_IMAGE_PATH],
    },
  };
}

function isSocialTrack(value: unknown): value is ApiDetailedTrack {
  if (!value || typeof value !== "object") return false;
  const candidate = value as Record<string, unknown>;
  const author = candidate.author;
  const narrator = candidate.narrator;

  return (
    typeof candidate.id === "string" &&
    typeof candidate.slug === "string" &&
    typeof candidate.title === "string" &&
    typeof candidate.duration === "number" &&
    Boolean(author) &&
    typeof author === "object" &&
    typeof (author as Record<string, unknown>).name === "string" &&
    Boolean(narrator) &&
    typeof narrator === "object" &&
    typeof (narrator as Record<string, unknown>).name === "string"
  );
}

function truncateDescription(value: string) {
  const normalized = value.replace(/\s+/g, " ").trim();
  return normalized.length <= SOCIAL_DESCRIPTION_LIMIT
    ? normalized
    : `${normalized.slice(0, SOCIAL_DESCRIPTION_LIMIT - 1).trimEnd()}…`;
}
