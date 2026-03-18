import type { Metadata } from "next";
import { DM_Mono, Plus_Jakarta_Sans } from "next/font/google";
import "./globals.css";

const jakartaSans = Plus_Jakarta_Sans({
  subsets: ["latin"],
  weight: ["400", "700", "800"],
  variable: "--font-display",
  display: "swap",
});

const dmMono = DM_Mono({
  subsets: ["latin"],
  weight: ["400", "500"],
  variable: "--font-mono",
  display: "swap",
});

export const metadata: Metadata = {
  title: "Fello AI — Account Intelligence",
  description: "Multi-agent AI pipeline converting visitor signals into sales intelligence.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>): React.ReactElement {
  return (
    <html lang="en" className={`dark ${jakartaSans.variable} ${dmMono.variable}`}>
      <body className="min-h-screen bg-background text-white antialiased font-sans">
        <header className="border-b border-border px-6 py-4 flex items-center gap-3">
          <span className="font-display font-bold text-xl tracking-tight text-white">
            Fello <span className="text-accent">AI</span>
          </span>
          <span className="text-muted text-sm font-mono">Account Intelligence</span>
        </header>
        <main className="mx-auto max-w-7xl px-6 py-8">{children}</main>
      </body>
    </html>
  );
}
