import type { Metadata } from "next";
import { headers } from "next/headers";
import KnotStudio from "./components/KnotStudio";

export async function generateMetadata(): Promise<Metadata> {
  const incoming = await headers();
  const host = incoming.get("host") ?? "localhost:3000";
  const protocol = incoming.get("x-forwarded-proto") ?? (host.startsWith("localhost") ? "http" : "https");
  const base = new URL(`${protocol}://${host}`);
  const title = "Knot Atelier — 扭结图工作台";
  const description = "支持平面扭结图、link 与 braid word 的本地矢量编辑器。";
  return {
    metadataBase: base,
    title,
    description,
    openGraph: {
      title,
      description,
      type: "website",
      images: [{ url: "/og.png", width: 1729, height: 909, alt: "Knot Atelier 扭结图编辑界面" }],
    },
    twitter: { card: "summary_large_image", title, description, images: ["/og.png"] },
  };
}

export default function Home() {
  return <KnotStudio />;
}
