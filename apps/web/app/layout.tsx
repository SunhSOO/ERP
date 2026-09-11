import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "GAILAB ERP Platform",
  description: "GAILAB ERP foundation shell",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="ko">
      <body>{children}</body>
    </html>
  );
}
