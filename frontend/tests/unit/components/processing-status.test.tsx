import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import {
  ProcessingStatus,
  ProcessingBadge,
} from "@/components/documents/processing-status";

describe("ProcessingStatus", () => {
  it("renders ready state with success message", () => {
    render(<ProcessingStatus state="ready" />);
    expect(screen.getByText("Ready for search")).toBeInTheDocument();
  });

  it("renders failed state with error message", () => {
    render(
      <ProcessingStatus state="failed" errorMessage="Parse error" />,
    );
    expect(screen.getByText(/Failed: Parse error/)).toBeInTheDocument();
  });

  it("renders in-progress state", () => {
    render(<ProcessingStatus state="chunking" />);
    expect(screen.getByText("chunking...")).toBeInTheDocument();
  });

  it("renders all 8 step indicators", () => {
    const { container } = render(<ProcessingStatus state="embedding" />);
    // 8 step circles + 7 connector lines
    const steps = container.querySelectorAll("[title]");
    expect(steps.length).toBe(8);
  });
});

describe("ProcessingBadge", () => {
  it("renders ready state with green styling", () => {
    const { container } = render(<ProcessingBadge state="ready" />);
    const badge = container.firstChild as HTMLElement;
    expect(badge.className).toContain("bg-green-100");
  });

  it("renders failed state with red styling", () => {
    const { container } = render(<ProcessingBadge state="failed" />);
    const badge = container.firstChild as HTMLElement;
    expect(badge.className).toContain("bg-red-100");
  });

  it("renders in-progress state with blue styling", () => {
    const { container } = render(<ProcessingBadge state="embedding" />);
    const badge = container.firstChild as HTMLElement;
    expect(badge.className).toContain("bg-blue-100");
  });
});
