import { tracks } from "@/data/tracks";
import type { Narrator } from "@/types";

const narratorProfiles = [
  {
    id: "narrator-aasha",
    slug: "aasha-karki",
    name: "आशा कार्की",
    image: "https://placehold.co/800x800/151311/f5eee7.png?text=AK",
    biography: "कोमल र स्पष्ट वाचनका लागि परिचित कविता तथा बालकथा वाचक।",
    followerCount: 28400,
  },
  {
    id: "narrator-bikram",
    slug: "bikram-rai",
    name: "विक्रम राई",
    image: "https://placehold.co/800x800/151311/f5eee7.png?text=BR",
    biography: "कथा र उपन्यासका पात्रलाई जीवन्त बनाउने गहिरो आवाजका वाचक।",
    followerCount: 25100,
  },
  {
    id: "narrator-dipti",
    slug: "dipti-bhandari",
    name: "दीप्ति भण्डारी",
    image: "https://placehold.co/800x800/151311/f5eee7.png?text=DB",
    biography: "भावपूर्ण कविता, पारिवारिक कथा र शान्त वाचनमा सक्रिय कलाकार।",
    followerCount: 22300,
  },
  {
    id: "narrator-kamal",
    slug: "kamal-adhikari",
    name: "कमल अधिकारी",
    image: "https://placehold.co/800x800/151311/f5eee7.png?text=KA",
    biography: "निबन्ध र विचारप्रधान साहित्यलाई सहज लयमा प्रस्तुत गर्ने वाचक।",
    followerCount: 19800,
  },
  {
    id: "narrator-nisha",
    slug: "nisha-tamang",
    name: "निशा तामाङ",
    image: "https://placehold.co/800x800/151311/f5eee7.png?text=NT",
    biography: "लोककथा र कवितामा न्यानो स्वर तथा सूक्ष्म भावका लागि चिनिएकी वाचक।",
    followerCount: 17600,
  },
  {
    id: "narrator-sujan",
    slug: "sujan-poudel",
    name: "सुजन पौडेल",
    image: "https://placehold.co/800x800/151311/f5eee7.png?text=SP",
    biography: "संवादप्रधान कथा र नाटकमा बहुरङ्गी आवाज प्रयोग गर्ने कलाकार।",
    followerCount: 15400,
  },
] as const;

export const narrators: Narrator[] = narratorProfiles.map((narrator) => ({
  ...narrator,
  narratedTracks: tracks.filter(
    (track) => track.narrator.id === narrator.id,
  ),
}));
