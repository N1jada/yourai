import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { VerificationBadge } from "@/components/citations/verification-badge";

describe("VerificationBadge", () => {
  it("renders verified status", () => {
    render(<VerificationBadge status="verified" />);
    expect(screen.getByText("Verified")).toBeInTheDocument();
  });

  it("renders unverified status", () => {
    render(<VerificationBadge status="unverified" />);
    expect(screen.getByText("Unverified")).toBeInTheDocument();
  });

  it("renders removed status", () => {
    render(<VerificationBadge status="removed" />);
    expect(screen.getByText("Removed")).toBeInTheDocument();
  });

  it("renders pre-1963 digitised status", () => {
    render(<VerificationBadge status="pre_1963_digitised" />);
    expect(screen.getByText("AI-digitised (pre-1963)")).toBeInTheDocument();
  });

  it("applies verified colour classes", () => {
    const { container } = render(<VerificationBadge status="verified" />);
    const badge = container.firstChild as HTMLElement;
    expect(badge.className).toContain("text-green-700");
    expect(badge.className).toContain("bg-green-50");
  });

  it("applies removed colour classes", () => {
    const { container } = render(<VerificationBadge status="removed" />);
    const badge = container.firstChild as HTMLElement;
    expect(badge.className).toContain("text-red-700");
  });

  it("applies custom className", () => {
    const { container } = render(
      <VerificationBadge status="verified" className="ml-2" />,
    );
    const badge = container.firstChild as HTMLElement;
    expect(badge.className).toContain("ml-2");
  });
});
