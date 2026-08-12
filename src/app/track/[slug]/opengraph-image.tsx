import { readFile } from "node:fs/promises";
import { join } from "node:path";

import { formatDuration } from "@/lib/formatters";
import { renderSocialCard } from "@/lib/social-card-renderer";
import {
  getSocialArtworkUrl,
  getSocialTrack,
} from "@/lib/social-metadata";

export const alt = "SunneKatha audio literature";
export const size = { width: 1200, height: 630 };
export const contentType = "image/jpeg";
export const runtime = "nodejs";
export const revalidate = 3600;

async function fetchArtwork(url: string): Promise<Buffer | undefined> {
  try {
    const response = await fetch(url, {
      cache: "force-cache",
      signal: AbortSignal.timeout(5_000),
    });

    if (!response.ok) return undefined;

    const contentType = response.headers.get("content-type") ?? "";
    if (!contentType.startsWith("image/")) return undefined;

    const bytes = await response.arrayBuffer();
    if (bytes.byteLength > 10 * 1024 * 1024) return undefined;

    return Buffer.from(bytes);
  } catch {
    return undefined;
  }
}

export default async function OpenGraphImage({
  params,
}: {
  params: Promise<{ slug: string }>;
}) {
  const { slug } = await params;
  const track = await getSocialTrack(slug);
  const artworkUrl = getSocialArtworkUrl(track?.coverImage);
  const [font, artwork] = await Promise.all([
    readFile(
      join(process.cwd(), "public/fonts/noto-sans-devanagari-regular.ttf"),
    ),
    fetchArtwork(artworkUrl),
  ]);

  const image = await renderSocialCard({
    title: track?.title || "Nepali literature, now in audio",
    author: track?.author.name || "SunneKatha",
    narrator: track?.narrator.name,
    category:
      track?.category?.name ||
      track?.literaryWork.category?.name ||
      "Audio literature",
    duration: track ? formatDuration(track.duration) : undefined,
    artwork,
    font,
  });

  return new Response(new Uint8Array(image), {
    headers: {
      "Content-Type": contentType,
      "Cache-Control":
        "public, max-age=3600, s-maxage=3600, stale-while-revalidate=86400",
    },
  });
}
