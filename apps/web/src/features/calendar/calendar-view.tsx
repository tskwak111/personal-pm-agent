import { FlexibleQueue, type FlexibleTask } from "./flexible-queue";

export type CalendarEvent = {
  id: string;
  title: string;
  kind: string;
  date: string;
};

export function CalendarView({
  events,
  flexibleTasks,
  connectionAction,
}: {
  events: CalendarEvent[];
  flexibleTasks: FlexibleTask[];
  connectionAction?: React.ReactNode;
}) {
  return (
    <main aria-label="캘린더 화면">
      <h1>캘린더</h1>
      {connectionAction}
      <section aria-label="캘린더 그리드">
        <ul>
          {events.map((e) => (
            <li key={e.id} data-kind={e.kind}>
              {e.date} {e.title}
            </li>
          ))}
        </ul>
      </section>
      {/* Flexible tasks are never placed on the time grid. */}
      <FlexibleQueue tasks={flexibleTasks} />
    </main>
  );
}
