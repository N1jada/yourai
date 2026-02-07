import { describe, it, expect } from "vitest";
import { render } from "@testing-library/react";
import {
  Skeleton,
  SkeletonRow,
  SkeletonMessage,
  SkeletonCard,
} from "@/components/ui/skeleton";

describe("Skeleton", () => {
  it("renders with aria-hidden", () => {
    const { container } = render(<Skeleton />);
    const el = container.firstChild as HTMLElement;
    expect(el).toHaveAttribute("aria-hidden", "true");
  });

  it("applies animate-pulse class", () => {
    const { container } = render(<Skeleton />);
    const el = container.firstChild as HTMLElement;
    expect(el.className).toContain("animate-pulse");
  });

  it("accepts custom className", () => {
    const { container } = render(<Skeleton className="h-8 w-32" />);
    const el = container.firstChild as HTMLElement;
    expect(el.className).toContain("h-8");
    expect(el.className).toContain("w-32");
  });
});

describe("SkeletonRow", () => {
  it("renders multiple skeleton elements", () => {
    const { container } = render(<SkeletonRow />);
    const skeletons = container.querySelectorAll("[aria-hidden='true']");
    expect(skeletons.length).toBeGreaterThanOrEqual(2);
  });
});

describe("SkeletonMessage", () => {
  it("renders three line skeletons", () => {
    const { container } = render(<SkeletonMessage />);
    const skeletons = container.querySelectorAll("[aria-hidden='true']");
    expect(skeletons.length).toBe(3);
  });
});

describe("SkeletonCard", () => {
  it("renders card with skeleton lines", () => {
    const { container } = render(<SkeletonCard />);
    const skeletons = container.querySelectorAll("[aria-hidden='true']");
    expect(skeletons.length).toBe(3);
  });

  it("has card styling", () => {
    const { container } = render(<SkeletonCard />);
    const card = container.firstChild as HTMLElement;
    expect(card.className).toContain("rounded-lg");
    expect(card.className).toContain("border");
  });
});
