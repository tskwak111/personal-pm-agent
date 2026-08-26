export type FlexibleTask = { id: string; title: string; minutes: number };

export function FlexibleQueue({ tasks }: { tasks: FlexibleTask[] }) {
  return (
    <section aria-label="아직 배치되지 않은 작업">
      <h2>아직 배치되지 않은 작업</h2>
      <ul>
        {tasks.map((t) => (
          <li key={t.id}>
            {t.title} ({t.minutes}분)
          </li>
        ))}
      </ul>
    </section>
  );
}
