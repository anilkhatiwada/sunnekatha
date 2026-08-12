import { describe, expect, it } from "vitest";

import {
  buildTrackMetadata,
  getSocialArtworkUrl,
} from "@/lib/social-metadata";
import type { ApiDetailedTrack } from "@/types/backend-api";

const track = {
  slug: "bansuri",
  title: "बाँसुरी छुटेको बिहान",
  description: "एक आत्मीय नेपाली कथा।",
  descriptionEnglish: "",
  duration: 120,
  author: { name: "अनिल खतिवडा" },
  narrator: { name: "वाचक" },
  category: { name: "कथा" },
  literaryWork: {},
} as ApiDetailedTrack;

describe("track social metadata", () => {
  it("uses real track data and a canonical encoded URL", () => {
    const metadata = buildTrackMetadata("बाँसुरी", track);

    expect(metadata).toMatchObject({
      title: "बाँसुरी छुटेको बिहान",
      description: "एक आत्मीय नेपाली कथा।",
      alternates: { canonical: "/track/%E0%A4%AC%E0%A4%BE%E0%A4%81%E0%A4%B8%E0%A5%81%E0%A4%B0%E0%A5%80" },
      openGraph: {
        siteName: "SunneKatha",
        locale: "ne_NP",
        title: "बाँसुरी छुटेको बिहान",
      },
      twitter: { card: "summary_large_image" },
    });
  });

  it("returns safe fallback metadata when the API is unavailable", () => {
    expect(buildTrackMetadata("missing", null)).toMatchObject({
      title: "Track",
      alternates: { canonical: "/track/missing" },
    });
  });

  it("only allows artwork from approved SunneKatha media hosts", () => {
    expect(
      getSocialArtworkUrl("https://media.sunnekatha.com/covers/track.jpg"),
    ).toBe("https://media.sunnekatha.com/covers/track.jpg");
    expect(getSocialArtworkUrl("http://127.0.0.1/private")).toBe(
      "https://sunnekatha.com/icons/pwa-512.png",
    );
    expect(getSocialArtworkUrl("https://example.com/untrusted.jpg")).toBe(
      "https://sunnekatha.com/icons/pwa-512.png",
    );
  });
});
