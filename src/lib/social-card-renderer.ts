import sharp from "sharp";

const WIDTH = 1200;
const HEIGHT = 630;
const waveform = [
  18, 30, 44, 27, 55, 38, 68, 46, 25, 58, 76, 42, 64, 32, 50, 72, 36, 22,
  48, 62, 28, 40, 69, 34,
];

export interface SocialCardInput {
  title: string;
  author: string;
  narrator?: string;
  category: string;
  duration?: string;
  artwork?: Buffer;
  font: Buffer;
}

export function escapeSvgText(value: string): string {
  return value
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&apos;");
}

function truncate(value: string, maxLength: number): string {
  return value.length > maxLength
    ? `${value.slice(0, maxLength - 1).trimEnd()}…`
    : value;
}

function artworkDataUri(artwork?: Buffer): string | null {
  if (!artwork) return null;
  return `data:image/jpeg;base64,${artwork.toString("base64")}`;
}

export async function renderSocialCard(input: SocialCardInput): Promise<Buffer> {
  const title = escapeSvgText(truncate(input.title, 54));
  const author = escapeSvgText(truncate(input.author, 38));
  const category = escapeSvgText(truncate(input.category, 20));
  const details = escapeSvgText(
    [input.narrator ? `वाचन: ${input.narrator}` : undefined, input.duration]
      .filter(Boolean)
      .join("  ·  "),
  );
  const fontData = input.font.toString("base64");
  const artwork = artworkDataUri(input.artwork);
  const titleSize = input.title.length > 42 ? 45 : 55;
  const bars = waveform
    .map((height, index) => {
      const x = 540 + index * 12;
      const y = 540 - height / 2;
      const fill = index % 4 === 0 ? "#e58a52" : "#615d5a";
      return `<rect x="${x}" y="${y}" width="5" height="${height}" rx="2.5" fill="${fill}"/>`;
    })
    .join("");

  const svg = `
    <svg width="${WIDTH}" height="${HEIGHT}" viewBox="0 0 ${WIDTH} ${HEIGHT}" xmlns="http://www.w3.org/2000/svg">
      <defs>
        <style>
          @font-face {
            font-family: 'Noto Sans Devanagari';
            src: url(data:font/ttf;base64,${fontData}) format('truetype');
            font-weight: 100 900;
          }
          text { font-family: 'Noto Sans Devanagari', sans-serif; }
        </style>
        <radialGradient id="warm" cx="0" cy="0" r="1" gradientTransform="translate(145 65) rotate(44) scale(590 420)">
          <stop stop-color="#3b2116" stop-opacity=".75"/>
          <stop offset="1" stop-color="#0b0a09" stop-opacity="0"/>
        </radialGradient>
        <clipPath id="coverClip"><rect x="62" y="104" width="420" height="420" rx="24"/></clipPath>
        <filter id="shadow" x="-30%" y="-30%" width="160%" height="180%">
          <feDropShadow dx="0" dy="20" stdDeviation="24" flood-color="#000" flood-opacity=".48"/>
        </filter>
      </defs>
      <rect width="1200" height="630" fill="#0b0a09"/>
      <rect width="1200" height="630" fill="url(#warm)"/>
      <rect x="24.5" y="24.5" width="1151" height="581" rx="30" fill="none" stroke="#d7ad63" stroke-opacity=".22"/>

      <g filter="url(#shadow)">
        <rect x="62" y="104" width="420" height="420" rx="24" fill="#1d1916"/>
        ${artwork ? `<image href="${artwork}" x="62" y="104" width="420" height="420" preserveAspectRatio="xMidYMid slice" clip-path="url(#coverClip)"/>` : ""}
      </g>
      <circle cx="427" cy="469" r="35" fill="#e58a52"/>
      <path d="M417 452 L417 486 L443 469 Z" fill="#f5eee7"/>

      <rect x="540" y="55" width="54" height="56" rx="15" fill="#e58a52"/>
      <text x="567" y="94" text-anchor="middle" font-size="32" font-weight="700" fill="#0b0a09">S</text>
      <text x="609" y="84" font-size="28" font-weight="700" fill="#f5eee7">SunneKatha</text>
      <text x="609" y="106" font-size="15" fill="#b7aaa0">सुन्ने कथा, सम्झिने शब्द</text>

      <rect x="1075" y="62" width="63" height="41" rx="21" fill="none" stroke="#d7ad63" stroke-opacity=".45"/>
      <text x="1106.5" y="89" text-anchor="middle" font-size="17" fill="#d7ad63">${category}</text>

      <text x="540" y="291" font-size="${titleSize}" font-weight="700" fill="#f5eee7">${title}</text>
      <text x="540" y="350" font-size="24" fill="#d7ad63">${author}</text>
      <text x="540" y="391" font-size="18" fill="#b7aaa0">${details}</text>

      ${bars}
      <rect x="955" y="511" width="183" height="64" rx="32" fill="#e58a52" fill-opacity=".14"/>
      <text x="1046.5" y="551" text-anchor="middle" font-size="19" fill="#e58a52">अहिले सुन्नुहोस् →</text>
    </svg>`;

  return sharp(Buffer.from(svg))
    .jpeg({
      quality: 84,
      chromaSubsampling: "4:2:0",
      mozjpeg: true,
    })
    .toBuffer();
}
