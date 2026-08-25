"use client";

import type { ButtonHTMLAttributes } from "react";

type ButtonProps = ButtonHTMLAttributes<HTMLButtonElement> & {
  variant?: "primary" | "ghost";
  "aria-expanded"?: boolean;
};

export function Button({ variant = "primary", className = "", ...rest }: ButtonProps) {
  const base =
    variant === "ghost"
      ? "bg-transparent hover:bg-[var(--color-surface)]"
      : "bg-[var(--color-accent)] text-white";
  return (
    <button
      className={`rounded-[var(--radius-md)] px-3 py-2 text-sm font-medium focus-visible:outline-2 focus-visible:outline-offset-2 ${base} ${className}`}
      {...rest}
    />
  );
}
