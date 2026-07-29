import { tracks } from "@/data/tracks";
import type { Author } from "@/types";

const DEMO_AUTHOR_IMAGE = "/images/demo/demo-author.webp";

const authorProfiles = [
  {
    id: "author-anjali",
    slug: "anjali-shrestha",
    name: "अञ्जली श्रेष्ठ",
    nameEnglish: "Anjali Shrestha",
    image: DEMO_AUTHOR_IMAGE,
    biography:
      "समकालीन भावना, प्रकृति र आत्मीय सम्बन्धलाई सरल भाषामा लेख्ने कवि।",
    birthYear: 1992,
    genres: ["poetry", "romance"],
  },
  {
    id: "author-bibek",
    slug: "bibek-lamsal",
    name: "विवेक लम्साल",
    nameEnglish: "Bibek Lamsal",
    image: DEMO_AUTHOR_IMAGE,
    biography:
      "सहर, गाउँ र बदलिँदो नेपाली समाजका पात्रहरूलाई कथामा उतार्ने लेखक।",
    birthYear: 1987,
    genres: ["short-story", "drama"],
  },
  {
    id: "author-chandra",
    slug: "chandra-kala-rai",
    name: "चन्द्रकला राई",
    nameEnglish: "Chandra Kala Rai",
    image: DEMO_AUTHOR_IMAGE,
    biography:
      "परिवार, स्मृति र सामाजिक न्यायका विषयमा कथा, कविता र नाटक लेख्ने सर्जक।",
    birthYear: 1979,
    genres: ["family", "poetry", "drama"],
  },
  {
    id: "author-deepak",
    slug: "deepak-subedi",
    name: "दीपक सुवेदी",
    nameEnglish: "Deepak Subedi",
    image: DEMO_AUTHOR_IMAGE,
    biography:
      "दर्शन, प्रविधि, प्रकृति र दैनिक जीवनबारे श्रव्य निबन्ध लेख्ने विचारक।",
    birthYear: 1983,
    genres: ["essay", "philosophy"],
  },
  {
    id: "author-elina",
    slug: "elina-gurung",
    name: "एलिना गुरुङ",
    nameEnglish: "Elina Gurung",
    image: DEMO_AUTHOR_IMAGE,
    biography:
      "नेपालका विभिन्न भूगोलका लोकविश्वास र मौखिक परम्परालाई नयाँ पुस्तासम्म पुर्‍याउने लेखक।",
    birthYear: 1989,
    genres: ["folk-tale", "heritage"],
  },
  {
    id: "author-farak",
    slug: "farak-drishti",
    name: "फरक दृष्टि",
    nameEnglish: "Farak Drishti",
    image: DEMO_AUTHOR_IMAGE,
    biography:
      "समकालीन नेपाली जीवनलाई वैकल्पिक दृष्टिकोणबाट प्रस्तुत गर्ने सामूहिक लेखन नाम।",
    genres: ["contemporary", "short-story"],
  },
  {
    id: "author-gauri",
    slug: "gauri-neupane",
    name: "गौरी न्यौपाने",
    nameEnglish: "Gauri Neupane",
    image: DEMO_AUTHOR_IMAGE,
    biography:
      "कल्पना, प्रकृति र सहानुभूतिको संसार रच्ने लोकप्रिय बालसाहित्य लेखक।",
    birthYear: 1990,
    genres: ["children", "fantasy"],
  },
  {
    id: "author-hemanta",
    slug: "hemanta-thapa",
    name: "हेमन्त थापा",
    nameEnglish: "Hemanta Thapa",
    image: DEMO_AUTHOR_IMAGE,
    biography:
      "परिवार, बसाइँसराइ र स्मृतिका तहहरू समेट्ने क्रमिक उपन्यासका लेखक।",
    birthYear: 1976,
    genres: ["novel", "family", "mystery"],
  },
] as const;

export const authors: Author[] = authorProfiles.map((author) => ({
  ...author,
  genres: [...author.genres],
  popularTracks: tracks
    .filter((track) => track.author.id === author.id)
    .sort((a, b) => b.playCount - a.playCount)
    .slice(0, 5),
}));
