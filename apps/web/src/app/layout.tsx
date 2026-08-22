import type { Metadata } from "next";

import "./globals.css";

export const metadata: Metadata = {
  title: "Personal PM Agent",
  description: "계획을 세우는 것이 아니라 유지하고 재조정합니다.",
};

export default function RootLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="ko">
      <body>{children}</body>
    </html>
  );
}
