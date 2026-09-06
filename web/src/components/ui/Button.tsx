import Link from "next/link";
import { cn } from "@/lib/cn";
import type { ReactNode } from "react";

type ButtonProps = {
  children: ReactNode;
  href?: string;
  onClick?: () => void;
  variant?: "filled" | "outline";
  size?: "md" | "lg";
  className?: string;
  type?: "button" | "submit";
};

export default function Button({
  children,
  href,
  onClick,
  variant = "filled",
  size = "lg",
  className,
  type = "button",
}: ButtonProps) {
  const classes = cn(
    "inline-flex items-center justify-center gap-2 rounded-full font-sans font-medium transition-all duration-300",
    size === "lg" ? "h-14 px-8 text-base" : "h-10 px-5 text-sm",
    variant === "filled"
      ? "bg-foreground text-background hover:opacity-85"
      : "bg-transparent text-foreground border border-foreground/20 hover:border-foreground/50",
    className
  );

  if (href) {
    return (
      <Link href={href} className={classes}>
        {children}
      </Link>
    );
  }

  return (
    <button type={type} onClick={onClick} className={classes}>
      {children}
    </button>
  );
}
