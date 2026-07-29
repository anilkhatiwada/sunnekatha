import {
  act,
  fireEvent,
  render,
  screen,
  waitFor,
} from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { PwaInstallButton } from "@/components/pwa/pwa-install-button";

describe("PwaInstallButton", () => {
  beforeEach(() => {
    vi.stubGlobal(
      "matchMedia",
      vi.fn().mockReturnValue({ matches: false }),
    );
  });

  it("offers the native install prompt when the browser makes it available", async () => {
    const prompt = vi.fn().mockResolvedValue(undefined);
    const installEvent = new Event("beforeinstallprompt");
    Object.assign(installEvent, {
      prompt,
      userChoice: Promise.resolve({ outcome: "accepted" }),
    });

    render(<PwaInstallButton />);
    act(() => {
      window.dispatchEvent(installEvent);
    });

    const installButton = await screen.findByRole("button", {
      name: "SunneKatha एप इन्स्टल गर्नुहोस्",
    });
    fireEvent.click(installButton);

    await waitFor(() => expect(prompt).toHaveBeenCalledOnce());
    await waitFor(() => expect(installButton).not.toBeInTheDocument());
  });

  it("stays hidden when installation is unavailable", () => {
    render(<PwaInstallButton />);

    expect(
      screen.queryByRole("button", {
        name: "SunneKatha एप इन्स्टल गर्नुहोस्",
      }),
    ).not.toBeInTheDocument();
  });
});
