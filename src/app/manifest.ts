import type { MetadataRoute } from "next";

export default function manifest(): MetadataRoute.Manifest {
  return {
    name: "SunneKatha — Nepali audio literature",
    short_name: "SunneKatha",
    description: "A calm digital home for Nepali stories, poetry, and literature.",
    start_url: "/",
    display: "standalone",
    background_color: "#0b0a09",
    theme_color: "#0b0a09",
    lang: "ne",
    orientation: "portrait-primary",
    categories: ["books", "entertainment", "music"],
    icons: [
      {
        src: "/icons/pwa-192.png",
        sizes: "192x192",
        type: "image/png",
        purpose: "any",
      },
      {
        src: "/icons/pwa-512.png",
        sizes: "512x512",
        type: "image/png",
        purpose: "any",
      },
      {
        src: "/icons/pwa-maskable-512.png",
        sizes: "512x512",
        type: "image/png",
        purpose: "maskable",
      },
    ],
  };
}
