import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { EmptyState } from "@/components/common/empty-state";
import { ErrorState } from "@/components/common/error-state";

describe("shared request states", () => {
  it("announces errors and invokes retry", () => {
    const onRetry = vi.fn();
    render(<ErrorState message="लोड भएन" onRetry={onRetry} />);

    expect(screen.getByRole("alert")).toHaveTextContent("लोड भएन");
    fireEvent.click(
      screen.getByRole("button", { name: "Try again" }),
    );
    expect(onRetry).toHaveBeenCalledOnce();
  });

  it("renders an actionable empty state without visual assumptions", () => {
    render(
      <EmptyState
        title="लाइब्रेरी खाली छ"
        description="मनपर्ने रचना यहाँ देखिनेछन्।"
      />,
    );

    expect(
      screen.getByRole("heading", { name: "लाइब्रेरी खाली छ" }),
    ).toBeVisible();
    expect(screen.getByText("मनपर्ने रचना यहाँ देखिनेछन्।")).toBeVisible();
  });
});
