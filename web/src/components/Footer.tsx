import Link from "next/link";
import { GithubLogo } from "@phosphor-icons/react/dist/ssr";

const COLUMNS: { title: string; links: { label: string; href: string }[] }[] = [
  {
    title: "Product",
    links: [
      { label: "Capabilities", href: "/#capabilities" },
      { label: "How it works", href: "/#how-it-works" },
      { label: "Try the app", href: "/try" },
    ],
  },
  {
    title: "Data",
    links: [
      { label: "Sentinel-2 L2A", href: "https://earth-search.aws.element84.com/v1" },
      { label: "ESA WorldCover", href: "https://esa-worldcover.org" },
      { label: "Bhuvan (ISRO/NRSC)", href: "https://bhuvan.nrsc.gov.in" },
    ],
  },
  {
    title: "Team",
    links: [
      { label: "About", href: "/about" },
      { label: "Model architecture", href: "/about#architecture" },
      { label: "PS-26015", href: "/about" },
    ],
  },
  {
    title: "Legal",
    links: [{ label: "Open Source", href: "https://github.com" }],
  },
];

export default function Footer() {
  return (
    <footer className="dot-grid-bg relative border-t border-foreground/10">
      <div className="mx-auto grid max-w-7xl grid-cols-2 gap-10 px-6 py-16 sm:px-10 md:grid-cols-5">
        <div className="col-span-2">
          <div className="font-display text-2xl tracking-tight">Watershed Signal</div>
          <p className="mt-3 max-w-xs text-sm text-muted-foreground">
            Geospatial land-cover and change detection for watershed development, built for
            SIH 2026 PS-26015.
          </p>
          <a
            href="https://github.com"
            className="mt-6 inline-flex h-10 w-10 items-center justify-center rounded-full border border-foreground/15 text-foreground/70 transition-colors hover:border-foreground/40 hover:text-foreground"
            aria-label="GitHub"
          >
            <GithubLogo size={18} weight="regular" />
          </a>
        </div>
        {COLUMNS.map((col) => (
          <div key={col.title}>
            <div className="font-mono text-xs uppercase tracking-wider text-muted-foreground">{col.title}</div>
            <ul className="mt-4 space-y-2.5">
              {col.links.map((link) => (
                <li key={link.label}>
                  <Link href={link.href} className="text-sm text-foreground/80 hover:text-foreground">
                    {link.label}
                  </Link>
                </li>
              ))}
            </ul>
          </div>
        ))}
      </div>
      <div className="mx-auto max-w-7xl border-t border-foreground/10 px-6 py-6 text-xs text-muted-foreground sm:px-10">
        Watershed Signal — Ministry of Rural Development, Smart India Hackathon 2026.
      </div>
    </footer>
  );
}
