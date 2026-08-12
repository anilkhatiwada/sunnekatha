import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { AddToPlaylistControl } from "@/features/playlist/add-to-playlist-control";

const mocks = vi.hoisted(() => ({
  addTrackToPlaylist: vi.fn(),
  createPlaylist: vi.fn(),
  getMyPlaylists: vi.fn(),
  useAuth: vi.fn(),
}));

vi.mock("@/features/auth/auth-provider", () => ({
  useAuth: mocks.useAuth,
}));

vi.mock("@/services", () => ({
  addTrackToPlaylist: mocks.addTrackToPlaylist,
  createPlaylist: mocks.createPlaylist,
  getMyPlaylists: mocks.getMyPlaylists,
  queryKeys: {
    playlists: {
      mine: () => ["playlists", "mine"],
      detail: (slug: string) => ["playlists", "detail", slug],
    },
  },
}));

const playlist = {
  id: "playlist-id",
  slug: "mero-sangraha",
  title: "मेरो सङ्ग्रह",
  description: "",
  coverImage: "/icons/pwa-192.png",
  curatorName: "User",
  trackCount: 2,
  totalDuration: 180,
  tracks: [],
  category: "user",
  isFeatured: false,
  visibility: "private" as const,
};

function renderControl(onMessage = vi.fn()) {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  render(
    <QueryClientProvider client={client}>
      <AddToPlaylistControl trackId="track-id" onMessage={onMessage} />
    </QueryClientProvider>,
  );
  return { onMessage };
}

describe("AddToPlaylistControl", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mocks.useAuth.mockReturnValue({ user: { id: "user-id" } });
    mocks.getMyPlaylists.mockResolvedValue([playlist]);
    mocks.addTrackToPlaylist.mockResolvedValue(playlist);
  });

  it("opens an accessible picker and adds to a large playlist row", async () => {
    const user = userEvent.setup();
    const { onMessage } = renderControl();

    await user.click(screen.getByRole("button", { name: "Add to playlist" }));

    expect(await screen.findByRole("dialog")).toBeInTheDocument();
    const playlistButton = await screen.findByRole("button", {
      name: "मेरो सङ्ग्रह 2 tracks · Private",
    });
    expect(playlistButton).toHaveClass("min-h-14");
    await user.click(playlistButton);

    await waitFor(() =>
      expect(mocks.addTrackToPlaylist).toHaveBeenCalledWith(
        "mero-sangraha",
        "track-id",
      ),
    );
    await waitFor(() =>
      expect(onMessage).toHaveBeenCalledWith("“मेरो सङ्ग्रह” — track added."),
    );
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
  });

  it("creates a private playlist and adds the track in one flow", async () => {
    const user = userEvent.setup();
    mocks.getMyPlaylists.mockResolvedValue([]);
    mocks.createPlaylist.mockResolvedValue({ ...playlist, slug: "naya" });
    mocks.addTrackToPlaylist.mockResolvedValue({ ...playlist, slug: "naya" });
    renderControl();

    await user.click(screen.getByRole("button", { name: "Add to playlist" }));
    await user.click(
      await screen.findByRole("button", {
        name: "Create a new playlist and add",
      }),
    );
    await user.type(
      screen.getByLabelText("New private playlist name"),
      "नयाँ सङ्ग्रह",
    );
    await user.click(screen.getByRole("button", { name: "Create and add" }));

    await waitFor(() =>
      expect(mocks.createPlaylist).toHaveBeenCalledWith({
        titleNe: "नयाँ सङ्ग्रह",
        visibility: "private",
      }),
    );
    await waitFor(() =>
      expect(mocks.addTrackToPlaylist).toHaveBeenCalledWith(
        "naya",
        "track-id",
      ),
    );
  });

  it("does not open the picker for signed-out users", async () => {
    const user = userEvent.setup();
    const onMessage = vi.fn();
    mocks.useAuth.mockReturnValue({ user: null });
    renderControl(onMessage);

    await user.click(screen.getByRole("button", { name: "Add to playlist" }));

    expect(onMessage).toHaveBeenCalledWith(
      "Sign in to add tracks to a playlist.",
    );
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
  });
});
