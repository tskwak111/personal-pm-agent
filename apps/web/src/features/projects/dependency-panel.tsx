export type Dependency = {
  id: string;
  label: string;
  owner?: string;
  isExternal: boolean;
};

export function DependencyPanel({ dependencies }: { dependencies: Dependency[] }) {
  return (
    <section aria-label="의존성">
      <h2>의존성</h2>
      <ul>
        {dependencies.map((dep) => (
          <li key={dep.id}>
            {dep.label}
            {dep.owner && <span> · 담당: {dep.owner}</span>}
            {dep.isExternal && <span data-external="true"> (외부 의존)</span>}
            {/* External dependencies are never actionable as our own tasks. */}
            {!dep.isExternal && <button type="button">완료 처리</button>}
          </li>
        ))}
      </ul>
    </section>
  );
}
