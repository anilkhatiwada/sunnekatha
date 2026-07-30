import { render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

const { useAuth } = vi.hoisted(() => ({
  useAuth: vi.fn(),
}));

vi.mock("@/features/auth/auth-provider", () => ({ useAuth }));

import { AuthRequired } from "@/features/auth/auth-required";

describe("AuthRequired", () => {
  beforeEach(() => {
    useAuth.mockReset();
  });

  it("does not render private content while the session is loading", () => {
    useAuth.mockReturnValue({ user: null, isLoading: true });

    render(<AuthRequired>Private library</AuthRequired>);

    expect(screen.queryByText("Private library")).not.toBeInTheDocument();
    expect(screen.queryByRole("link")).not.toBeInTheDocument();
  });

  it("offers sign-in without exposing private content to anonymous users", () => {
    useAuth.mockReturnValue({ user: null, isLoading: false });

    render(<AuthRequired>Private library</AuthRequired>);

    expect(screen.queryByText("Private library")).not.toBeInTheDocument();
    expect(
      screen.getByRole("link", { name: "साइन इन गर्नुहोस्" }),
    ).toHaveAttribute("href", "/login");
  });

  it("renders private content for the authenticated user", () => {
    useAuth.mockReturnValue({
      user: { id: "user-id", displayName: "आरती" },
      isLoading: false,
    });

    render(<AuthRequired>Private library</AuthRequired>);

    expect(screen.getByText("Private library")).toBeVisible();
  });
});
