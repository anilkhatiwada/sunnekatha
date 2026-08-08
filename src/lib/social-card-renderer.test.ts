import { describe, expect, it } from "vitest";

import { escapeSvgText } from "@/lib/social-card-renderer";

describe("social card renderer", () => {
  it("preserves Devanagari text for the shaping renderer", () => {
    expect(escapeSvgText("बाँसुरी छुटेको बिहान")).toBe("बाँसुरी छुटेको बिहान");
  });

  it("escapes untrusted text before placing it in SVG", () => {
    expect(escapeSvgText('<script title="x">&')).toBe(
      "&lt;script title=&quot;x&quot;&gt;&amp;",
    );
  });
});
