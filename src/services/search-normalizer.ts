const DEVANAGARI_CONSONANTS: Record<string, string> = {
  क: "ka",
  ख: "kha",
  ग: "ga",
  घ: "gha",
  ङ: "nga",
  च: "cha",
  छ: "chha",
  ज: "ja",
  झ: "jha",
  ञ: "nya",
  ट: "ta",
  ठ: "tha",
  ड: "da",
  ढ: "dha",
  ण: "na",
  त: "ta",
  थ: "tha",
  द: "da",
  ध: "dha",
  न: "na",
  प: "pa",
  फ: "pha",
  ब: "ba",
  भ: "bha",
  म: "ma",
  य: "ya",
  र: "ra",
  ल: "la",
  व: "va",
  श: "sha",
  ष: "sha",
  स: "sa",
  ह: "ha",
  क्ष: "kshya",
  त्र: "tra",
  ज्ञ: "gya",
};

const DEVANAGARI_VOWELS: Record<string, string> = {
  अ: "a",
  आ: "aa",
  इ: "i",
  ई: "ii",
  उ: "u",
  ऊ: "uu",
  ए: "e",
  ऐ: "ai",
  ओ: "o",
  औ: "au",
};

const DEVANAGARI_MATRAS: Record<string, string> = {
  "ा": "aa",
  "ि": "i",
  "ी": "ii",
  "ु": "u",
  "ू": "uu",
  "े": "e",
  "ै": "ai",
  "ो": "o",
  "ौ": "au",
  "ृ": "ri",
};

export function normalizeSearchText(value: string) {
  return value
    .normalize("NFKC")
    .toLocaleLowerCase()
    .replace(/[’'".,!?।:;()[\]{}_-]/g, " ")
    .replace(/\s+/g, " ")
    .trim();
}

export function romanizeNepali(value: string) {
  let romanized = "";

  for (const character of value.normalize("NFKC")) {
    if (DEVANAGARI_CONSONANTS[character]) {
      romanized += DEVANAGARI_CONSONANTS[character];
      continue;
    }

    if (DEVANAGARI_MATRAS[character]) {
      romanized = romanized.replace(/a$/, "");
      romanized += DEVANAGARI_MATRAS[character];
      continue;
    }

    if (character === "्") {
      romanized = romanized.replace(/a$/, "");
      continue;
    }

    if (character === "ं" || character === "ँ") {
      romanized += "n";
      continue;
    }

    romanized += DEVANAGARI_VOWELS[character] ?? character;
  }

  return normalizeRomanizedText(romanized);
}

export function normalizeRomanizedText(value: string) {
  return normalizeSearchText(value)
    .replace(/aa+/g, "a")
    .replace(/ii+/g, "i")
    .replace(/uu+/g, "u")
    .replace(/v/g, "b")
    .replace(/a\b/g, "");
}

export function searchValuesMatch(
  values: Array<string | undefined>,
  query: string,
) {
  const nativeQuery = normalizeSearchText(query);
  const romanQuery = normalizeRomanizedText(romanizeNepali(query));
  const queryVariants = [...new Set([nativeQuery, romanQuery])].filter(Boolean);

  return values.some((value) => {
    if (!value) return false;

    const variants = [
      normalizeSearchText(value),
      normalizeRomanizedText(romanizeNepali(value)),
    ];

    return variants.some((variant) =>
      queryVariants.some((queryVariant) => variant.includes(queryVariant)),
    );
  });
}
