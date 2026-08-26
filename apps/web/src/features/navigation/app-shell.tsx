"use client";

import Link from "next/link";
import { useState } from "react";

import { Button } from "../../components/ui/button";

const DESTINATIONS = [
  { href: "/today", label: "오늘" },
  { href: "/inbox", label: "인박스" },
  { href: "/projects", label: "프로젝트" },
  { href: "/calendar", label: "캘린더" },
  { href: "/review", label: "리뷰" },
] as const;

export function AppShell({ children }: { children: React.ReactNode }) {
  const [agentOpen, setAgentOpen] = useState(false);

  return (
    <div className="min-h-dvh md:grid md:grid-cols-[15rem_minmax(0,1fr)]">
      <nav
        aria-label="주요 메뉴"
        className="hidden md:block border-r border-[var(--color-border)] p-4"
      >
        <ul>
          {DESTINATIONS.map((d) => (
            <li key={d.href}>
              <Link
                href={d.href}
                className="block rounded px-3 py-2 text-sm hover:bg-[var(--color-surface)]"
              >
                {d.label}
              </Link>
            </li>
          ))}
        </ul>
        <Button
          variant="ghost"
          aria-expanded={agentOpen}
          onClick={() => setAgentOpen((v) => !v)}
          className="mt-4"
        >
          에이전트 열기
        </Button>
      </nav>

      <main id="main-content" tabIndex={-1}>
        {children}
      </main>

      <aside aria-label="에이전트 패널" data-open={agentOpen} hidden={!agentOpen}>
        <p>에이전트</p>
      </aside>

      <nav
        aria-label="모바일 메뉴"
        className="fixed inset-x-0 bottom-0 flex justify-around border-t border-[var(--color-border)] bg-[var(--color-bg)] p-2 md:hidden"
      >
        {DESTINATIONS.map((d) => (
          <Link key={d.href} href={d.href} className="px-2 py-1 text-xs">
            {d.label}
          </Link>
        ))}
        <Button
          variant="ghost"
          aria-expanded={agentOpen}
          onClick={() => setAgentOpen((v) => !v)}
          className="text-xs"
        >
          에이전트 열기
        </Button>
      </nav>
    </div>
  );
}
