import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Knot Atelier — 扭结图工作台",
  description: "一个独立、可扩展的二维扭结与辫图编辑器。",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="zh-CN">
      <body>{children}</body>
    </html>
  );
}
