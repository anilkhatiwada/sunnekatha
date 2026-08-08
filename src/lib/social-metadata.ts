import type { Metadata } from "next";

import { environment } from "@/config/environment";
import type { ApiDetailedTrack } from "@/types/backend-api";

export const SITE_URL = "https://sunnekatha.com";
const SOCIAL_DESCRIPTION_LIMIT = 180;
const SOCIAL_ARTWORK_HOSTS = new Set([
  "media.sunnekatha.com",
  "sunnekatha.com",
  "www.sunnekatha.com",
  "sunnekatha-prod-media-533463644243-ap-south-1.s3.amazonaws.com",
]);

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
      title: "रचना",
      description: "SunneKatha मा नेपाली श्रव्य साहित्य सुन्नुहोस्।",
      alternates: { canonical: canonicalPath },
    };
  }

  const creator = track.author.name;
  const category = track.category?.name || track.literaryWork.category?.name;
  const fallbackDescription = [creator, category, "SunneKatha मा सुन्नुहोस्"]
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
    },
    twitter: {
      card: "summary_large_image",
      title: track.title,
      description,
    },
  };
}

export function getSocialArtworkUrl(value: string | null | undefined) {
  const fallback = `${SITE_URL}/icons/pwa-512.png`;
  if (!value) return fallback;

  try {
    const url = new URL(value, SITE_URL);
    return url.protocol === "https:" && SOCIAL_ARTWORK_HOSTS.has(url.hostname)
      ? url.toString()
      : fallback;
  } catch {
    return fallback;
  }
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
