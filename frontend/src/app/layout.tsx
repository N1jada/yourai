import type { Metadata } from "next";
import { Providers } from "@/lib/providers/providers";
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
      <body className="antialiased">
        <a href="#main-content" className="skip-to-content">
          Skip to content
        </a>
        <Providers>{children}</Providers>
      </body>
    </html>
  );
}
