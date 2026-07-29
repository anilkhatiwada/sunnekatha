import { tracks } from "@/data/tracks";
import type { Playlist, Track } from "@/types";

const DEMO_COVERS = {
  literary: "/images/demo/monsoon-literature.webp",
  journey: "/images/demo/himalayan-letter.webp",
  folklore: "/images/demo/folk-tale-lakhe.webp",
  reflective: "/images/demo/moonlit-listening.webp",
} as const;

function selectTracks(ids: string[]): Track[] {
  const trackById = new Map(tracks.map((track) => [track.id, track]));

  return ids.map((id) => {
    const track = trackById.get(id);

    if (!track) {
      throw new Error(`Playlist references unknown track: ${id}`);
    }

    return track;
  });
}

function createPlaylist(
  playlist: Omit<Playlist, "trackCount" | "totalDuration" | "tracks"> & {
    trackIds: string[];
  },
): Playlist {
  const { trackIds, ...metadata } = playlist;
  const selectedTracks = selectTracks(trackIds);

  return {
    ...metadata,
    tracks: selectedTracks,
    trackCount: selectedTracks.length,
    totalDuration: selectedTracks.reduce(
      (total, track) => total + track.duration,
      0,
    ),
  };
}

export const playlists: Playlist[] = [
  createPlaylist({
    id: "playlist-001",
    slug: "sunnai-parne-nepali-kavita",
    title: "सुन्नैपर्ने नेपाली कविता",
    description: "समकालीन भाव, प्रेम, प्रकृति र स्मृतिका प्रिय कविता।",
    coverImage: DEMO_COVERS.reflective,
    curatorName: "SunneKatha सम्पादकीय",
    category: "कविता",
    isFeatured: true,
    trackIds: ["track-001", "track-009", "track-013", "track-017", "track-024"],
  }),
  createPlaylist({
    id: "playlist-002",
    slug: "balkatha",
    title: "बालकथा",
    description: "कल्पना, प्रकृति र साना साहसले भरिएका परिवारमैत्री कथा।",
    coverImage: DEMO_COVERS.journey,
    curatorName: "SunneKatha Kids",
    category: "बालसाहित्य",
    isFeatured: true,
    trackIds: ["track-007", "track-011", "track-015", "track-022"],
  }),
  createPlaylist({
    id: "playlist-003",
    slug: "jiwan-ra-darshan",
    title: "जीवन र दर्शन",
    description: "दैनिक जीवनलाई नयाँ आँखाले हेर्न प्रेरित गर्ने श्रव्य निबन्ध।",
    coverImage: DEMO_COVERS.reflective,
    curatorName: "SunneKatha विचार",
    category: "निबन्ध",
    isFeatured: true,
    trackIds: ["track-004", "track-010", "track-019", "track-013"],
  }),
  createPlaylist({
    id: "playlist-004",
    slug: "nepali-lokkatha",
    title: "नेपाली लोककथा",
    description: "लोकविश्वास, जात्रा, हिमाल र पुस्तौंदेखि सुनिँदै आएका कथा।",
    coverImage: DEMO_COVERS.folklore,
    curatorName: "SunneKatha लोक",
    category: "लोककथा",
    isFeatured: true,
    trackIds: ["track-005", "track-011", "track-020"],
  }),
  createPlaylist({
    id: "playlist-005",
    slug: "premka-kavita",
    title: "प्रेमका कविता",
    description: "माया, दूरी, प्रतीक्षा र आत्मीयताका कोमल शब्दहरू।",
    coverImage: DEMO_COVERS.journey,
    curatorName: "SunneKatha कविता",
    category: "प्रेम",
    isFeatured: false,
    trackIds: ["track-001", "track-017", "track-024", "track-013"],
  }),
  createPlaylist({
    id: "playlist-006",
    slug: "barshako-saanjh",
    title: "वर्षाको साँझ",
    description: "पानीको आवाजसँग सुहाउने शान्त, स्मृतिमय कथा र कविता।",
    coverImage: DEMO_COVERS.literary,
    curatorName: "SunneKatha साँझ",
    category: "मूड",
    isFeatured: true,
    trackIds: ["track-002", "track-003", "track-014", "track-017"],
  }),
  createPlaylist({
    id: "playlist-007",
    slug: "saharka-katha",
    title: "सहरका कथा",
    description: "व्यस्त गल्ली, चिया पसल र आधुनिक सम्बन्धका आवाजहरू।",
    coverImage: DEMO_COVERS.literary,
    curatorName: "SunneKatha कथा",
    category: "समकालीन",
    isFeatured: false,
    trackIds: ["track-006", "track-012", "track-019", "track-021"],
  }),
  createPlaylist({
    id: "playlist-008",
    slug: "lamo-yatraka-lagi",
    title: "लामो यात्राका लागि",
    description: "उपन्यासका अध्याय र लामो कथासँग बिताउने श्रव्य यात्रा।",
    coverImage: DEMO_COVERS.journey,
    curatorName: "SunneKatha यात्रा",
    category: "लामो श्रवण",
    isFeatured: false,
    trackIds: ["track-008", "track-016", "track-023", "track-018"],
  }),
];
