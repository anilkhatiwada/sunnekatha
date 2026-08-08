import { readFile } from "node:fs/promises";
import { join } from "node:path";

import { ImageResponse } from "next/og";

import { formatDuration } from "@/lib/formatters";
import {
  getSocialArtworkUrl,
  getSocialTrack,
} from "@/lib/social-metadata";

export const alt = "SunneKatha श्रव्य साहित्य";
export const size = { width: 1200, height: 630 };
export const contentType = "image/png";
export const runtime = "nodejs";

const waveform = [
  18, 30, 44, 27, 55, 38, 68, 46, 25, 58, 76, 42, 64, 32, 50, 72, 36, 22,
  48, 62, 28, 40, 69, 34,
];

export default async function OpenGraphImage({
  params,
}: {
  params: Promise<{ slug: string }>;
}) {
  const { slug } = await params;
  const [track, font] = await Promise.all([
    getSocialTrack(slug),
    readFile(
      join(
        process.cwd(),
        "public/fonts/noto-sans-devanagari-regular.ttf",
      ),
    ),
  ]);
  const coverImage = getSocialArtworkUrl(track?.coverImage);
  const title = track?.title || "नेपाली साहित्य अब कानसम्म";
  const author = track?.author.name || "SunneKatha";
  const narrator = track?.narrator.name;
  const category =
    track?.category?.name || track?.literaryWork.category?.name || "श्रव्य साहित्य";
  const duration = track ? formatDuration(track.duration) : null;

  return new ImageResponse(
    (
      <div
        style={{
          width: "100%",
          height: "100%",
          display: "flex",
          position: "relative",
          overflow: "hidden",
          background: "#0b0a09",
          color: "#f5eee7",
          fontFamily: "Noto Sans Devanagari",
        }}
      >
        <div
          style={{
            position: "absolute",
            inset: 0,
            display: "flex",
            background:
              "radial-gradient(circle at 12% 10%, rgba(229,138,82,.26), transparent 42%), radial-gradient(circle at 90% 90%, rgba(215,173,99,.16), transparent 38%)",
          }}
        />
        <div
          style={{
            position: "absolute",
            inset: 24,
            display: "flex",
            border: "1px solid rgba(215,173,99,.22)",
            borderRadius: 30,
          }}
        />

        <div
          style={{
            width: "100%",
            height: "100%",
            display: "flex",
            padding: "54px 62px",
            position: "relative",
          }}
        >
          <div
            style={{
              width: 420,
              height: 420,
              display: "flex",
              position: "relative",
              marginTop: 50,
              flexShrink: 0,
            }}
          >
            <img
              src={coverImage}
              alt=""
              width="420"
              height="420"
              style={{
                width: 420,
                height: 420,
                objectFit: "cover",
                borderRadius: 24,
                boxShadow: "0 28px 70px rgba(0,0,0,.48)",
              }}
            />
            <div
              style={{
                position: "absolute",
                right: 20,
                bottom: 20,
                width: 70,
                height: 70,
                borderRadius: 999,
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                background: "#e58a52",
                color: "#0b0a09",
                fontSize: 34,
                boxShadow: "0 12px 32px rgba(0,0,0,.38)",
              }}
            >
              ▶
            </div>
          </div>

          <div
            style={{
              minWidth: 0,
              flex: 1,
              display: "flex",
              flexDirection: "column",
              marginLeft: 58,
            }}
          >
            <div
              style={{
                display: "flex",
                alignItems: "center",
                justifyContent: "space-between",
              }}
            >
              <div style={{ display: "flex", alignItems: "center" }}>
                <div
                  style={{
                    width: 54,
                    height: 54,
                    borderRadius: 15,
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "center",
                    background: "#e58a52",
                    color: "#0b0a09",
                    fontSize: 32,
                    fontWeight: 700,
                  }}
                >
                  S
                </div>
                <div
                  style={{
                    marginLeft: 15,
                    display: "flex",
                    flexDirection: "column",
                  }}
                >
                  <span style={{ fontSize: 28, fontWeight: 700 }}>SunneKatha</span>
                  <span style={{ fontSize: 15, color: "#b7aaa0" }}>
                    सुन्ने कथा, सम्झिने शब्द
                  </span>
                </div>
              </div>
              <span
                style={{
                  display: "flex",
                  border: "1px solid rgba(215,173,99,.35)",
                  borderRadius: 999,
                  padding: "9px 16px",
                  color: "#d7ad63",
                  fontSize: 17,
                }}
              >
                {category}
              </span>
            </div>

            <div
              style={{
                flex: 1,
                display: "flex",
                flexDirection: "column",
                justifyContent: "center",
                paddingTop: 12,
              }}
            >
              <div
                style={{
                  display: "flex",
                  fontSize: title.length > 42 ? 45 : 55,
                  lineHeight: 1.22,
                  fontWeight: 700,
                  maxHeight: 144,
                  overflow: "hidden",
                }}
              >
                {title}
              </div>
              <div
                style={{
                  display: "flex",
                  marginTop: 20,
                  fontSize: 24,
                  color: "#d7ad63",
                }}
              >
                {author}
              </div>
              <div
                style={{
                  display: "flex",
                  marginTop: 8,
                  fontSize: 18,
                  color: "#b7aaa0",
                }}
              >
                {[narrator ? `वाचन: ${narrator}` : null, duration]
                  .filter(Boolean)
                  .join("  ·  ")}
              </div>
            </div>

            <div
              style={{
                display: "flex",
                alignItems: "center",
                justifyContent: "space-between",
              }}
            >
              <div
                style={{
                  height: 54,
                  display: "flex",
                  alignItems: "center",
                  gap: 7,
                }}
              >
                {waveform.map((height, index) => (
                  <span
                    key={index}
                    style={{
                      width: 5,
                      height,
                      display: "flex",
                      borderRadius: 999,
                      background:
                        index % 4 === 0
                          ? "#e58a52"
                          : "rgba(245,238,231,.35)",
                    }}
                  />
                ))}
              </div>
              <div
                style={{
                  display: "flex",
                  alignItems: "center",
                  borderRadius: 999,
                  padding: "13px 22px",
                  background: "rgba(229,138,82,.14)",
                  color: "#e58a52",
                  fontSize: 19,
                }}
              >
                अहिले सुन्नुहोस्&nbsp; →
              </div>
            </div>
          </div>
        </div>
      </div>
    ),
    {
      ...size,
      fonts: [
        {
          name: "Noto Sans Devanagari",
          data: font,
          style: "normal",
          weight: 400,
        },
      ],
    },
  );
}
