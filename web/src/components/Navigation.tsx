"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { cn } from "@/lib/cn";
import Button from "@/components/ui/Button";
import { ShieldCheck, User, SignOut, CheckCircle, X } from "@phosphor-icons/react";
import { useAuth } from "@/lib/auth";
import ModelStatusModal from "@/components/ModelStatusModal";
import AuthModal from "@/components/AuthModal";

const LINKS = [
  { href: "/#capabilities", label: "Capabilities" },
  { href: "/about", label: "About" },
  { href: "/how-to-use", label: "How to Use" },
];

function NavLink({ href, label, highlight }: { href: string; label: string; highlight?: boolean }) {
  return (
    <Link
      href={href}
      className={cn(
        "group relative font-sans text-sm transition-colors",
        highlight
          ? "text-amber font-semibold hover:text-amber/90"
          : "text-foreground/80 hover:text-foreground"
      )}
    >
      {label}
      <span
        className={cn(
          "absolute -bottom-1 left-0 h-px w-0 transition-all duration-300 group-hover:w-full",
          highlight ? "bg-amber" : "bg-foreground"
        )}
      />
    </Link>
  );
}

export default function Navigation() {
  const { user, isAdmin, isLoaded, logout, notification, clearNotification } = useAuth();
  const [scrolled, setScrolled] = useState(false);
  const [showModelModal, setShowModelModal] = useState(false);
  const [showAuthModal, setShowAuthModal] = useState(false);

  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 50);
    onScroll();
    window.addEventListener("scroll", onScroll, { passive: true });
    return () => window.removeEventListener("scroll", onScroll);
  }, []);

  return (
    <>
      <header className="sticky top-0 z-50">
        <div
          className={cn(
            "flex items-center justify-between transition-all duration-500",
            scrolled
              ? "mx-4 mt-4 rounded-2xl border border-foreground/10 bg-background/95 px-6 py-3 shadow-sm backdrop-blur-md"
              : "mx-0 mt-0 rounded-none border-transparent bg-transparent px-6 py-3.5 sm:px-10 sm:py-4"
          )}
        >
          <div className="flex items-center gap-3 sm:gap-4">
            <Link href="/" className="font-sans text-lg font-semibold tracking-tight text-foreground">
              Watershed Signal
            </Link>
            <button
              onClick={() => setShowModelModal(true)}
              className="hidden md:inline-flex items-center gap-1.5 rounded-full border border-foreground/15 bg-foreground/5 px-3 py-1 font-mono text-[11px] text-foreground/80 hover:border-foreground/40 hover:text-foreground transition-all cursor-pointer"
              title="Inspect Model 1 U-Net checkpoint & architecture"
            >
              <span className="h-1.5 w-1.5 rounded-full bg-sage animate-pulse" />
              <span>Model 1 · 49.1% IoU</span>
            </button>
          </div>

          <div className="flex items-center gap-4 sm:gap-6">
            <nav className="hidden items-center gap-7 md:flex">
              {LINKS.map((link) => (
                <NavLink key={link.href} {...link} />
              ))}
              {/* Statutory Audit link for Admin */}
              {isLoaded && isAdmin && (
                <NavLink href="/audit" label="Audit Console" highlight={true} />
              )}
            </nav>

            {/* Officer Role & Profile Badge + Log Out Button */}
            <div className="flex items-center gap-2">
              {isLoaded && user ? (
                <>
                  <button
                    type="button"
                    onClick={() => setShowAuthModal(true)}
                    className={cn(
                      "flex items-center gap-1.5 sm:gap-2 rounded-full border px-3 py-1 font-mono text-xs transition-all cursor-pointer shadow-xs",
                      isAdmin
                        ? "border-amber/40 bg-amber/10 text-amber hover:bg-amber/20"
                        : "border-sage/40 bg-sage/10 text-sage hover:bg-sage/20"
                    )}
                    title="Click to view officer profile or switch role"
                  >
                    {isAdmin ? (
                      <ShieldCheck size={14} weight="bold" />
                    ) : (
                      <User size={14} weight="bold" />
                    )}
                    <span className="font-semibold uppercase tracking-wider text-[11px]">
                      {isAdmin ? "Admin" : "Official"}
                    </span>
                    <span className="hidden lg:inline text-foreground/70 font-sans text-xs">
                      · {user.name.split(" ")[0]}
                    </span>
                  </button>

                  <button
                    type="button"
                    onClick={logout}
                    className="flex items-center gap-1 rounded-full border border-foreground/15 bg-foreground/5 px-2.5 py-1 font-mono text-[11px] text-muted-foreground hover:border-danger/40 hover:bg-danger/10 hover:text-danger transition-all cursor-pointer"
                    title="Log out of session"
                  >
                    <SignOut size={13} weight="bold" />
                    <span className="hidden sm:inline">Log Out</span>
                  </button>
                </>
              ) : (
                <button
                  type="button"
                  onClick={() => setShowAuthModal(true)}
                  className="flex items-center gap-1.5 rounded-full border border-foreground/20 bg-foreground/5 px-3 py-1 font-mono text-xs text-foreground hover:border-foreground hover:bg-foreground/10 transition-all cursor-pointer shadow-xs"
                >
                  <User size={14} weight="bold" />
                  <span>Select Role / Sign In</span>
                </button>
              )}
            </div>

            <Button href="/try" size="md">
              Open the App →
            </Button>
          </div>
        </div>
      </header>

      {/* Gentle Session Notification Pop-up Toast */}
      {notification && (
        <div className="fixed bottom-6 right-6 z-50 flex items-center gap-3 rounded-2xl border border-foreground/15 bg-background/95 px-4 py-3 shadow-2xl backdrop-blur-md animate-fade-in font-mono text-xs text-foreground">
          <CheckCircle size={18} weight="bold" className="text-sage shrink-0" />
          <span>{notification}</span>
          <button
            type="button"
            onClick={clearNotification}
            className="ml-2 rounded-md p-1 text-muted-foreground hover:text-foreground transition-colors cursor-pointer"
            aria-label="Dismiss notification"
          >
            <X size={14} weight="bold" />
          </button>
        </div>
      )}

      <ModelStatusModal isOpen={showModelModal} onClose={() => setShowModelModal(false)} />
      <AuthModal isOpen={showAuthModal} onClose={() => setShowAuthModal(false)} />
    </>
  );
}
