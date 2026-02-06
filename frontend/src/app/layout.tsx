import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "YourAI",
  description:
    "AI-powered knowledge assistant and policy compliance platform for regulated industries",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body className="bg-[var(--color-background)] text-[var(--color-foreground)] antialiased">
        {children}
      </body>
    </html>
  );
}
