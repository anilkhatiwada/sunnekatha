import { describe, expect, it } from "vitest";

import {
  formatDuration,
  formatPlayerTime,
  getProgressPercentage,
} from "@/lib/formatters";

describe("time formatting", () => {
  it.each([
    [0, "0:00"],
    [65, "1:05"],
    [3661, "1:01:01"],
    [-1, "0:00"],
    [Number.NaN, "0:00"],
  ])("formats %s seconds as %s", (seconds, expected) => {
    expect(formatPlayerTime(seconds)).toBe(expected);
  });

  it("formats literary durations and clamps progress percentages", () => {
    expect(formatDuration(59)).toBe("0 मिनेट");
    expect(formatDuration(3660)).toBe("1 घण्टा 1 मिनेट");
    expect(getProgressPercentage(150, 100)).toBe(100);
    expect(getProgressPercentage(-10, 100)).toBe(0);
  });
});
