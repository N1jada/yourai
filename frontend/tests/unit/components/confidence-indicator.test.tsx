import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { ConfidenceIndicator } from "@/components/confidence/confidence-indicator";

describe("ConfidenceIndicator", () => {
  it("renders high confidence", () => {
    render(<ConfidenceIndicator level="high" />);
    const el = screen.getByRole("status");
    expect(el).toHaveAttribute("aria-label", "Confidence: High confidence");
    expect(el).toHaveTextContent("High confidence");
  });

  it("renders medium confidence", () => {
    render(<ConfidenceIndicator level="medium" />);
    const el = screen.getByRole("status");
    expect(el).toHaveAttribute("aria-label", "Confidence: Medium confidence");
    expect(el).toHaveTextContent("Medium confidence");
  });

  it("renders low confidence", () => {
    render(<ConfidenceIndicator level="low" />);
    const el = screen.getByRole("status");
    expect(el).toHaveAttribute("aria-label", "Confidence: Low confidence");
    expect(el).toHaveTextContent("Low confidence");
  });

  it("shows custom reason as title", () => {
    render(<ConfidenceIndicator level="high" reason="Multiple sources" />);
    const el = screen.getByRole("status");
    expect(el).toHaveAttribute("title", "Multiple sources");
  });

  it("shows default description as title when no reason", () => {
    render(<ConfidenceIndicator level="low" />);
    const el = screen.getByRole("status");
    expect(el).toHaveAttribute(
      "title",
      "Limited sources available — verify this information independently",
    );
  });

  it("applies appropriate colour classes", () => {
    render(<ConfidenceIndicator level="high" />);
    const el = screen.getByRole("status");
    expect(el.className).toContain("bg-green-100");
    expect(el.className).toContain("text-green-800");
  });

  it("has decorative dot that is aria-hidden", () => {
    const { container } = render(<ConfidenceIndicator level="medium" />);
    const dot = container.querySelector("[aria-hidden='true']");
    expect(dot).toBeInTheDocument();
  });

  it("applies custom className", () => {
    render(<ConfidenceIndicator level="high" className="mt-4" />);
    const el = screen.getByRole("status");
    expect(el.className).toContain("mt-4");
  });
});
