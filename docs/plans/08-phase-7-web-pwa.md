# Phase 7 — Next.js Web/PWA User Experience Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement the approved responsive Web/PWA: AI Life Audit onboarding, Today, Inbox, Projects, Calendar, Review/Approval and global Agent panel with fast task actions, explicit sync states and accessible interaction.

**Architecture:** Feature modules consume the generated OpenAPI client. Server state is cached separately from local UI state. Desktop uses persistent navigation and Agent side panel; mobile uses bottom navigation and quick capture. Critical writes wait for server verification.

**Tech Stack:** Next.js 16 App Router, React 19.2, TypeScript strict, Tailwind CSS, accessible primitives, TanStack Query, generated API client, Vitest, Testing Library, MSW, Playwright and axe.

**Spec:** Design sections 6, 16, 17 and UX gates; generated API contracts.

## Global Constraints

- Follow `AGENTS.md`, the approved specs and exact Phase interface contracts.
- LLMs generate candidates and language; deterministic services authorize and execute.
- User-facing state must distinguish fact, inference, proposal, internal execution and external execution.
- Use TDD and fresh verification before every completion claim.
- Update implementation status and traceability after every Task.

---

## Locked File Map

```text
apps/web/src/
├─ app/(auth)/
├─ app/(app)/today/
├─ app/(app)/inbox/
├─ app/(app)/projects/
├─ app/(app)/calendar/
├─ app/(app)/review/
├─ features/onboarding/
├─ features/today/
├─ features/inbox/
├─ features/projects/
├─ features/calendar/
├─ features/review/
├─ features/agent/
├─ components/ui/
├─ lib/api/
├─ lib/query/
├─ lib/accessibility/
└─ test/
```

### Task P7-T01: Create design tokens, accessible primitives and responsive application shell

**Files:**
- Create: `apps/web/src/app/globals.css`
- Create: `apps/web/src/components/ui/button.tsx`
- Create: `apps/web/src/components/ui/card.tsx`
- Create: `apps/web/src/components/ui/status-badge.tsx`
- Create: `apps/web/src/features/navigation/app-shell.tsx`
- Create: `apps/web/src/test/app-shell.test.tsx`

**Interfaces:**
- Consumes: Next.js bootstrap and product navigation contract
- Produces: desktop sidebar, mobile bottom navigation, global quick capture and Agent panel region

- [ ] **Step 1: Write the failing test**

```tsx
import { render, screen } from "@testing-library/react";
import { AppShell } from "../features/navigation/app-shell";

it("exposes the five primary destinations", () => {
  render(<AppShell><div>content</div></AppShell>);
  for (const name of ["오늘", "인박스", "프로젝트", "캘린더", "리뷰"]) {
    expect(screen.getAllByRole("link", { name })[0]).toBeVisible();
  }
});

it("has a keyboard reachable agent trigger", () => {
  render(<AppShell><div>content</div></AppShell>);
  expect(screen.getByRole("button", { name: "에이전트 열기" })).toHaveAttribute("aria-expanded", "false");
});
```

- [ ] **Step 2: Run the focused test and confirm the intended failure**

```bash
pnpm --filter @personal-pm/web test -- --run src/test/app-shell.test.tsx
```

Expected: FAIL because the application shell is absent.

- [ ] **Step 3: Implement the minimum contract**

```tsx
export function AppShell({ children }: { children: React.ReactNode }) {
  return (
    <div className="min-h-dvh md:grid md:grid-cols-[15rem_minmax(0,1fr)]">
      <PrimaryNavigation />
      <main id="main-content" tabIndex={-1}>{children}</main>
      <AgentPanel />
      <MobileQuickCapture />
    </div>
  );
}
```

- [ ] **Step 4: Run the focused test and confirm it passes**

```bash
pnpm --filter @personal-pm/web test -- --run src/test/app-shell.test.tsx
```

Expected: PASS with zero failures.

- [ ] **Step 5: Run adjacent verification**

```bash
pnpm --filter @personal-pm/web lint && pnpm --filter @personal-pm/web typecheck
```

- [ ] **Step 6: Commit the reviewable unit**

```bash
git add apps/web/src/app/globals.css apps/web/src/components/ui/button.tsx apps/web/src/components/ui/card.tsx apps/web/src/components/ui/status-badge.tsx apps/web/src/features/navigation/app-shell.tsx apps/web/src/test/app-shell.test.tsx
git commit -m "feat(web): add responsive application shell"
```

### Task P7-T02: Implement authenticated routing and AI Life Audit onboarding

**Files:**
- Create: `apps/web/src/app/(auth)/sign-in/page.tsx`
- Create: `apps/web/src/app/(app)/onboarding/page.tsx`
- Create: `apps/web/src/features/onboarding/onboarding-flow.tsx`
- Create: `apps/web/src/features/onboarding/use-onboarding.ts`
- Create: `apps/web/src/test/onboarding.test.tsx`

**Interfaces:**
- Consumes: identity endpoints, Calendar connection status and upload APIs
- Produces: five-stage onboarding with minimal profile, source import, grouped findings, conflict questions and initial report approval

- [ ] **Step 1: Write the failing test**

```tsx
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { OnboardingFlow } from "../features/onboarding/onboarding-flow";

it("does not ask facts already found in imported sources", async () => {
  render(<OnboardingFlow initialAnalysis={analysisWithKnownTimezone} />);
  await userEvent.click(screen.getByRole("button", { name: "계속" }));
  expect(screen.queryByLabelText("시간대")).not.toBeInTheDocument();
  expect(screen.getByText("날짜 충돌 2개")).toBeVisible();
});
```

- [ ] **Step 2: Run the focused test and confirm the intended failure**

```bash
pnpm --filter @personal-pm/web test -- --run src/test/onboarding.test.tsx
```

Expected: FAIL because onboarding is absent.

- [ ] **Step 3: Implement the minimum contract**

```tsx
const steps: OnboardingStep[] = [
  { id: "basics", title: "기본 정보" },
  { id: "sources", title: "기존 자료" },
  { id: "analysis", title: "자동 구조" },
  { id: "questions", title: "필요한 확인" },
  { id: "report", title: "초기 상황 보고서" },
];
```

- [ ] **Step 4: Run the focused test and confirm it passes**

```bash
pnpm --filter @personal-pm/web test -- --run src/test/onboarding.test.tsx
```

Expected: PASS with zero failures.

- [ ] **Step 5: Run adjacent verification**

```bash
pnpm --filter @personal-pm/web typecheck && pnpm --filter @personal-pm/web lint
```

- [ ] **Step 6: Commit the reviewable unit**

```bash
git add apps/web/src/app/(auth)/sign-in/page.tsx apps/web/src/app/(app)/onboarding/page.tsx apps/web/src/features/onboarding/onboarding-flow.tsx apps/web/src/features/onboarding/use-onboarding.ts apps/web/src/test/onboarding.test.tsx
git commit -m "feat(web): implement AI Life Audit onboarding"
```

### Task P7-T03: Implement Today screen and one-action task execution

**Files:**
- Create: `apps/web/src/app/(app)/today/page.tsx`
- Create: `apps/web/src/features/today/today-view.tsx`
- Create: `apps/web/src/features/today/task-action-bar.tsx`
- Create: `apps/web/src/features/today/risk-card.tsx`
- Create: `apps/web/src/test/today-view.test.tsx`

**Interfaces:**
- Consumes: today plan API, Work Session commands and proposal summaries
- Produces: core outcome, fixed events, must-do, queue, not-today, risks and start/complete/partial/block/replan actions

- [ ] **Step 1: Write the failing test**

```tsx
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

it("shows why the core outcome is selected", () => {
  render(<TodayView plan={todayPlanFixture} />);
  expect(screen.getByText("오늘의 핵심 결과")).toBeVisible();
  expect(screen.getByText(/Base Pass/)).toBeVisible();
});

it("starts a ready task with one action", async () => {
  render(<TodayView plan={todayPlanFixture} />);
  await userEvent.click(screen.getByRole("button", { name: "ERD 작성 시작" }));
  expect(startSessionMock).toHaveBeenCalledTimes(1);
});
```

- [ ] **Step 2: Run the focused test and confirm the intended failure**

```bash
pnpm --filter @personal-pm/web test -- --run src/test/today-view.test.tsx
```

Expected: FAIL because Today components are absent.

- [ ] **Step 3: Implement the minimum contract**

```tsx
export function TaskActionBar({ task }: { task: TodayTask }) {
  return (
    <div aria-label={`${task.title} 작업`}>
      <Button onClick={() => startSession(task.id)}>{task.title} 시작</Button>
      <TaskOverflowMenu task={task} actions={["완료", "부분 완료", "막힘", "오늘 제외"]} />
    </div>
  );
}
```

- [ ] **Step 4: Run the focused test and confirm it passes**

```bash
pnpm --filter @personal-pm/web test -- --run src/test/today-view.test.tsx
```

Expected: PASS with zero failures.

- [ ] **Step 5: Run adjacent verification**

```bash
pnpm --filter @personal-pm/web typecheck && pnpm --filter @personal-pm/web lint
```

- [ ] **Step 6: Commit the reviewable unit**

```bash
git add apps/web/src/app/(app)/today/page.tsx apps/web/src/features/today/today-view.tsx apps/web/src/features/today/task-action-bar.tsx apps/web/src/features/today/risk-card.tsx apps/web/src/test/today-view.test.tsx
git commit -m "feat(web): implement Today execution flow"
```

### Task P7-T04: Implement Inbox review, source comparison and batch confirmation

**Files:**
- Create: `apps/web/src/app/(app)/inbox/page.tsx`
- Create: `apps/web/src/features/inbox/inbox-list.tsx`
- Create: `apps/web/src/features/inbox/candidate-card.tsx`
- Create: `apps/web/src/features/inbox/source-evidence.tsx`
- Create: `apps/web/src/test/inbox.test.tsx`

**Interfaces:**
- Consumes: Inbox/candidate APIs and source artifact metadata
- Produces: status filters, original-versus-interpretation view, conflict choices and project-level batch actions

- [ ] **Step 1: Write the failing test**

```tsx
it("shows unknown deadline time instead of invented time", () => {
  render(<CandidateCard candidate={dateOnlyDeadlineCandidate} />);
  expect(screen.getByText("마감 시각 미확인")).toBeVisible();
  expect(screen.queryByText("23:59")).not.toBeInTheDocument();
});

it("requires an explicit source choice for conflicting deadlines", () => {
  render(<CandidateCard candidate={conflictingDeadlineCandidate} />);
  expect(screen.getByRole("radio", { name: /강의계획서/ })).toBeVisible();
  expect(screen.getByRole("radio", { name: /최근 과제 공지/ })).toBeVisible();
});
```

- [ ] **Step 2: Run the focused test and confirm the intended failure**

```bash
pnpm --filter @personal-pm/web test -- --run src/test/inbox.test.tsx
```

Expected: FAIL because Inbox review components are absent.

- [ ] **Step 3: Implement the minimum contract**

```tsx
export function SourceEvidence({ sources }: { sources: CandidateSource[] }) {
  return (
    <section aria-labelledby="source-evidence-heading">
      <h3 id="source-evidence-heading">근거 원본</h3>
      {sources.map((source) => <SourceSnippet key={source.id} source={source} />)}
    </section>
  );
}
```

- [ ] **Step 4: Run the focused test and confirm it passes**

```bash
pnpm --filter @personal-pm/web test -- --run src/test/inbox.test.tsx
```

Expected: PASS with zero failures.

- [ ] **Step 5: Run adjacent verification**

```bash
pnpm --filter @personal-pm/web typecheck && pnpm --filter @personal-pm/web lint
```

- [ ] **Step 6: Commit the reviewable unit**

```bash
git add apps/web/src/app/(app)/inbox/page.tsx apps/web/src/features/inbox/inbox-list.tsx apps/web/src/features/inbox/candidate-card.tsx apps/web/src/features/inbox/source-evidence.tsx apps/web/src/test/inbox.test.tsx
git commit -m "feat(web): implement source-backed Inbox"
```

### Task P7-T05: Implement Project health, milestones, bottlenecks and dependencies

**Files:**
- Create: `apps/web/src/app/(app)/projects/page.tsx`
- Create: `apps/web/src/app/(app)/projects/[workstreamId]/page.tsx`
- Create: `apps/web/src/features/projects/project-header.tsx`
- Create: `apps/web/src/features/projects/milestone-timeline.tsx`
- Create: `apps/web/src/features/projects/dependency-panel.tsx`
- Create: `apps/web/src/test/project-detail.test.tsx`

**Interfaces:**
- Consumes: Workstream, milestone, task and risk APIs
- Produces: project list/detail with progress separated from schedule risk and explicit waiting/blocked states

- [ ] **Step 1: Write the failing test**

```tsx
it("does not equate effort progress with deadline health", () => {
  render(<ProjectHeader project={highProgressHighRiskProject} />);
  expect(screen.getByText("실행 진행률 82%")).toBeVisible();
  expect(screen.getByText("마감 가능성 High")).toBeVisible();
});

it("shows external dependency owner without presenting it as our task", () => {
  render(<DependencyPanel dependencies={[externalDatasetDependency]} />);
  expect(screen.getByText("담당: 민수")).toBeVisible();
  expect(screen.queryByRole("button", { name: "완료 처리" })).not.toBeInTheDocument();
});
```

- [ ] **Step 2: Run the focused test and confirm the intended failure**

```bash
pnpm --filter @personal-pm/web test -- --run src/test/project-detail.test.tsx
```

Expected: FAIL because Project detail components are absent.

- [ ] **Step 3: Implement the minimum contract**

```tsx
export function ProjectHeader({ project }: { project: ProjectHealth }) {
  return (
    <header>
      <h1>{project.title}</h1>
      <Metric label="실행 진행률" value={`${project.executionProgress}%`} />
      <Metric label="마감 가능성" value={project.riskLevel} />
      <StatusExplanation reasons={project.riskReasons} />
    </header>
  );
}
```

- [ ] **Step 4: Run the focused test and confirm it passes**

```bash
pnpm --filter @personal-pm/web test -- --run src/test/project-detail.test.tsx
```

Expected: PASS with zero failures.

- [ ] **Step 5: Run adjacent verification**

```bash
pnpm --filter @personal-pm/web typecheck && pnpm --filter @personal-pm/web lint
```

- [ ] **Step 6: Commit the reviewable unit**

```bash
git add apps/web/src/app/(app)/projects/page.tsx apps/web/src/app/(app)/projects/[workstreamId]/page.tsx apps/web/src/features/projects/project-header.tsx apps/web/src/features/projects/milestone-timeline.tsx apps/web/src/features/projects/dependency-panel.tsx apps/web/src/test/project-detail.test.tsx
git commit -m "feat(web): implement project health views"
```

### Task P7-T06: Implement Calendar with fixed events, focus blocks, sync state and flexible queue

**Files:**
- Create: `apps/web/src/app/(app)/calendar/page.tsx`
- Create: `apps/web/src/features/calendar/calendar-view.tsx`
- Create: `apps/web/src/features/calendar/sync-status.tsx`
- Create: `apps/web/src/features/calendar/flexible-queue.tsx`
- Create: `apps/web/src/test/calendar-view.test.tsx`

**Interfaces:**
- Consumes: Calendar event, sync status and focus proposal APIs
- Produces: distinct visuals for fixed, tentative, focus and date-only deadline items plus internal/external result status

- [ ] **Step 1: Write the failing test**

```tsx
it("distinguishes internal save from external failure", () => {
  render(<SyncStatus status={{ internal: "SAVED", external: "FAILED", reason: "AUTH_EXPIRED" }} />);
  expect(screen.getByText("앱 내부 저장 완료")).toBeVisible();
  expect(screen.getByText("Google Calendar 반영 실패")).toBeVisible();
});

it("keeps flexible tasks outside the calendar grid", () => {
  render(<CalendarView events={calendarEvents} flexibleTasks={flexibleTasks} />);
  expect(screen.getByRole("region", { name: "아직 배치되지 않은 작업" })).toBeVisible();
});
```

- [ ] **Step 2: Run the focused test and confirm the intended failure**

```bash
pnpm --filter @personal-pm/web test -- --run src/test/calendar-view.test.tsx
```

Expected: FAIL because Calendar components are absent.

- [ ] **Step 3: Implement the minimum contract**

```tsx
export function SyncStatus({ status }: { status: CalendarSyncStatus }) {
  if (status.external === "FAILED") {
    return <Alert title="앱 내부 저장 완료" description={`Google Calendar 반영 실패: ${status.reason}`} />;
  }
  return <StatusBadge>Google Calendar 반영 완료</StatusBadge>;
}
```

- [ ] **Step 4: Run the focused test and confirm it passes**

```bash
pnpm --filter @personal-pm/web test -- --run src/test/calendar-view.test.tsx
```

Expected: PASS with zero failures.

- [ ] **Step 5: Run adjacent verification**

```bash
pnpm --filter @personal-pm/web typecheck && pnpm --filter @personal-pm/web lint
```

- [ ] **Step 6: Commit the reviewable unit**

```bash
git add apps/web/src/app/(app)/calendar/page.tsx apps/web/src/features/calendar/calendar-view.tsx apps/web/src/features/calendar/sync-status.tsx apps/web/src/features/calendar/flexible-queue.tsx apps/web/src/test/calendar-view.test.tsx
git commit -m "feat(web): implement Calendar sync experience"
```

### Task P7-T07: Implement weekly Review and Approval Center

**Files:**
- Create: `apps/web/src/app/(app)/review/page.tsx`
- Create: `apps/web/src/features/review/weekly-review.tsx`
- Create: `apps/web/src/features/review/proposal-card.tsx`
- Create: `apps/web/src/features/review/approval-center.tsx`
- Create: `apps/web/src/test/review-and-approval.test.tsx`

**Interfaces:**
- Consumes: review, proposal, approval and audit APIs
- Produces: weekly outcomes, capacity comparison, overload choices, next-three outcomes and approve/modify/reject/undo

- [ ] **Step 1: Write the failing test**

```tsx
it("shows before, after, saved time and resulting risk", () => {
  render(<ProposalCard proposal={overloadProposal} />);
  expect(screen.getByText("예상 절감 180분")).toBeVisible();
  expect(screen.getByText("High → Medium")).toBeVisible();
  expect(screen.getByRole("button", { name: "승인" })).toBeVisible();
});

it("does not show undo for irreversible proposal", () => {
  render(<ProposalCard proposal={irreversibleProposal} />);
  expect(screen.queryByRole("button", { name: "되돌리기" })).not.toBeInTheDocument();
});
```

- [ ] **Step 2: Run the focused test and confirm the intended failure**

```bash
pnpm --filter @personal-pm/web test -- --run src/test/review-and-approval.test.tsx
```

Expected: FAIL because Review and Approval components are absent.

- [ ] **Step 3: Implement the minimum contract**

```tsx
export function ProposalCard({ proposal }: { proposal: ProposalView }) {
  return (
    <Card>
      <ProposalDiff before={proposal.beforeState} after={proposal.proposedState} />
      <Impact minutes={proposal.minutesSavedOrAdded} risk={proposal.resultingRisk} />
      <ProposalActions proposal={proposal} />
    </Card>
  );
}
```

- [ ] **Step 4: Run the focused test and confirm it passes**

```bash
pnpm --filter @personal-pm/web test -- --run src/test/review-and-approval.test.tsx
```

Expected: PASS with zero failures.

- [ ] **Step 5: Run adjacent verification**

```bash
pnpm --filter @personal-pm/web typecheck && pnpm --filter @personal-pm/web lint
```

- [ ] **Step 6: Commit the reviewable unit**

```bash
git add apps/web/src/app/(app)/review/page.tsx apps/web/src/features/review/weekly-review.tsx apps/web/src/features/review/proposal-card.tsx apps/web/src/features/review/approval-center.tsx apps/web/src/test/review-and-approval.test.tsx
git commit -m "feat(web): implement review and approval flows"
```

### Task P7-T08: Implement global Agent panel with resumable operation streaming

**Files:**
- Create: `apps/web/src/features/agent/agent-panel.tsx`
- Create: `apps/web/src/features/agent/operation-stream.ts`
- Create: `apps/web/src/features/agent/operation-timeline.tsx`
- Create: `apps/web/src/test/agent-panel.test.tsx`

**Interfaces:**
- Consumes: Agent message and SSE operation APIs
- Produces: quick capture, message history, operation steps, structured result cards and stream resume

- [ ] **Step 1: Write the failing test**

```tsx
it("renders operation progress without claiming success before verify", async () => {
  render(<AgentPanel initialOperation={operationBeforeVerify} />);
  expect(screen.getByText("외부 반영 확인 중")).toBeVisible();
  expect(screen.queryByText("완료되었습니다")).not.toBeInTheDocument();
});

it("reconnects with the last event id", () => {
  const stream = createOperationStream({ operationId: "op-1", lastEventId: "42" });
  expect(stream.url.searchParams.get("last_event_id")).toBe("42");
});
```

- [ ] **Step 2: Run the focused test and confirm the intended failure**

```bash
pnpm --filter @personal-pm/web test -- --run src/test/agent-panel.test.tsx
```

Expected: FAIL because Agent panel and stream client are absent.

- [ ] **Step 3: Implement the minimum contract**

```tsx
export function createOperationStream({ operationId, lastEventId }: StreamOptions) {
  const url = new URL(`/api/v1/agent/operations/${operationId}/stream`, window.location.origin);
  if (lastEventId) url.searchParams.set("last_event_id", lastEventId);
  return { url, source: new EventSource(url) };
}
```

- [ ] **Step 4: Run the focused test and confirm it passes**

```bash
pnpm --filter @personal-pm/web test -- --run src/test/agent-panel.test.tsx
```

Expected: PASS with zero failures.

- [ ] **Step 5: Run adjacent verification**

```bash
pnpm --filter @personal-pm/web typecheck && pnpm --filter @personal-pm/web lint
```

- [ ] **Step 6: Commit the reviewable unit**

```bash
git add apps/web/src/features/agent/agent-panel.tsx apps/web/src/features/agent/operation-stream.ts apps/web/src/features/agent/operation-timeline.tsx apps/web/src/test/agent-panel.test.tsx
git commit -m "feat(web): stream Agent operations"
```

### Task P7-T09: Add PWA manifest, service worker and opt-in Web Push

**Files:**
- Create: `apps/web/src/app/manifest.ts`
- Create: `apps/web/public/sw.js`
- Create: `apps/web/src/features/notifications/push-settings.tsx`
- Create: `apps/web/src/test/pwa.test.ts`

**Interfaces:**
- Consumes: notification settings and subscription endpoints
- Produces: installable PWA shell, safe cache policy and explicit push opt-in

- [ ] **Step 1: Write the failing test**

```tsx
it("manifest defines standalone display and product icons", async () => {
  const manifest = await appManifest();
  expect(manifest.display).toBe("standalone");
  expect(manifest.icons?.length).toBeGreaterThan(0);
});

it("never caches authenticated API responses", () => {
  const source = readServiceWorkerSource();
  expect(source).not.toMatch(/\/api\/v1.*cache\.put/);
});
```

- [ ] **Step 2: Run the focused test and confirm the intended failure**

```bash
pnpm --filter @personal-pm/web test -- --run src/test/pwa.test.ts
```

Expected: FAIL because PWA assets are absent.

- [ ] **Step 3: Implement the minimum contract**

```tsx
export default function manifest(): MetadataRoute.Manifest {
  return {
    name: "Personal PM Agent",
    short_name: "PM Agent",
    start_url: "/today",
    display: "standalone",
    background_color: "#ffffff",
    theme_color: "#111827",
    icons: [{ src: "/icons/icon-192.png", sizes: "192x192", type: "image/png" }],
  };
}
```

- [ ] **Step 4: Run the focused test and confirm it passes**

```bash
pnpm --filter @personal-pm/web test -- --run src/test/pwa.test.ts
```

Expected: PASS with zero failures.

- [ ] **Step 5: Run adjacent verification**

```bash
pnpm --filter @personal-pm/web build
```

- [ ] **Step 6: Commit the reviewable unit**

```bash
git add apps/web/src/app/manifest.ts apps/web/public/sw.js apps/web/src/features/notifications/push-settings.tsx apps/web/src/test/pwa.test.ts
git commit -m "feat(web): add installable PWA and push opt-in"
```

### Task P7-T10: Create critical browser E2E, accessibility and interaction-time instrumentation

**Files:**
- Create: `apps/web/e2e/onboarding.spec.ts`
- Create: `apps/web/e2e/today.spec.ts`
- Create: `apps/web/e2e/inbox.spec.ts`
- Create: `apps/web/e2e/calendar.spec.ts`
- Create: `apps/web/e2e/approval.spec.ts`
- Create: `apps/web/e2e/accessibility.spec.ts`
- Create: `apps/web/src/lib/analytics/ux-events.ts`

**Interfaces:**
- Consumes: all Phase 7 screens and test API fixtures
- Produces: Playwright coverage for the complete core loop and UX-001 through UX-006 event timing

- [ ] **Step 1: Write the failing test**

```tsx
import { test, expect } from "@playwright/test";

test("task start is one user action", async ({ page }) => {
  await page.goto("/today");
  await page.getByRole("button", { name: "ERD 작성 시작" }).click();
  await expect(page.getByText("진행 중")).toBeVisible();
  const events = await page.evaluate(() => window.__uxEvents);
  expect(events.filter((event) => event.name === "task_started")).toHaveLength(1);
});

test("critical pages have no serious axe violations", async ({ page }) => {
  await page.goto("/today");
  const results = await new AxeBuilder({ page }).analyze();
  expect(results.violations.filter((v) => ["critical", "serious"].includes(v.impact ?? ""))).toEqual([]);
});
```

- [ ] **Step 2: Run the focused test and confirm the intended failure**

```bash
pnpm --filter @personal-pm/web e2e --grep "task start|axe"
```

Expected: FAIL because browser tests and UX instrumentation are absent.

- [ ] **Step 3: Implement the minimum contract**

```tsx
export function recordUxEvent(name: UxEventName, startedAt: number, metadata: Record<string, string> = {}) {
  navigator.sendBeacon("/api/v1/analytics/ux-events", JSON.stringify({
    name,
    duration_ms: Math.round(performance.now() - startedAt),
    metadata,
  }));
}
```

- [ ] **Step 4: Run the focused test and confirm it passes**

```bash
pnpm --filter @personal-pm/web e2e --grep "task start|axe"
```

Expected: PASS with zero failures.

- [ ] **Step 5: Run adjacent verification**

```bash
pnpm --filter @personal-pm/web test -- --run && pnpm --filter @personal-pm/web e2e && pnpm --filter @personal-pm/web build
```

- [ ] **Step 6: Commit the reviewable unit**

```bash
git add apps/web/e2e/onboarding.spec.ts apps/web/e2e/today.spec.ts apps/web/e2e/inbox.spec.ts apps/web/e2e/calendar.spec.ts apps/web/e2e/approval.spec.ts apps/web/e2e/accessibility.spec.ts apps/web/src/lib/analytics/ux-events.ts
git commit -m "test(web): cover critical PWA journeys"
```

## Phase 7 Exit Criteria

- [x] Desktop and mobile navigation expose Today, Inbox, Projects, Calendar and Review.
- [x] Onboarding completes the approved AI Life Audit flow.
- [x] Task start takes one action and completion/partial/block takes no more than two.
- [x] Source conflicts and unknown deadline times are visible and never silently normalized.
- [x] Internal versus external Calendar status is explicit.
- [x] Agent panel does not display success before Verify.
- [x] Critical screens have zero serious accessibility violations.
- [x] Core browser E2E and production build pass.
