import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = { title: "Apex F1", description: "Formula 1 intelligence dashboard" };
export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return <html lang="en"><body>{children}</body></html>;
}
