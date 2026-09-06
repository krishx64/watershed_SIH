"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { cn } from "@/lib/cn";
import Button from "@/components/ui/Button";

const LINKS = [
  { href: "/#capabilities", label: "Capabilities" },
  { href: "/about", label: "About" },
  { href: "/how-to-use", label: "How to Use" },
];

function NavLink({ href, label }: { href: string; label: string }) {
  return (
    <Link href={href} className="group relative font-sans text-sm text-foreground/80 hover:text-foreground">
      {label}
      <span className="absolute -bottom-1 left-0 h-px w-0 bg-foreground transition-all duration-300 group-hover:w-full" />
    </Link>
  );
}

export default function Navigation() {
  const [scrolled, setScrolled] = useState(false);

  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 50);
    onScroll();
    window.addEventListener("scroll", onScroll, { passive: true });
    return () => window.removeEventListener("scroll", onScroll);
  }, []);

  return (
    <header className="sticky top-0 z-50">
      <div
        className={cn(
          "flex items-center justify-between transition-all duration-500",
          scrolled
            ? "mx-4 mt-4 rounded-2xl border border-foreground/10 bg-background/95 px-6 py-3 shadow-sm backdrop-blur-md"
            : "mx-0 mt-0 rounded-none border-transparent bg-transparent px-6 py-5 sm:px-10"
        )}
      >
        <Link href="/" className="font-display text-xl tracking-tight">
          Watershed Signal
        </Link>
        <nav className="hidden items-center gap-8 md:flex">
          {LINKS.map((link) => (
            <NavLink key={link.href} {...link} />
          ))}
        </nav>
        <Button href="/try" size="md">
          Open the App →
        </Button>
      </div>
    </header>
  );
}
