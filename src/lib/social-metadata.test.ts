import { describe, expect, it } from "vitest";

import {
  buildTrackMetadata,
  SOCIAL_IMAGE,
  SOCIAL_IMAGE_PATH,
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
        images: [SOCIAL_IMAGE],
      },
      twitter: {
        card: "summary_large_image",
        images: [SOCIAL_IMAGE_PATH],
      },
    });
  });

  it("returns safe fallback metadata when the API is unavailable", () => {
    expect(buildTrackMetadata("missing", null)).toMatchObject({
      title: "Track",
      alternates: { canonical: "/track/missing" },
      openGraph: { images: [SOCIAL_IMAGE] },
      twitter: { images: [SOCIAL_IMAGE_PATH] },
    });
  });
});
