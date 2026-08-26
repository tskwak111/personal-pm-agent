export type CandidateSource = {
  id: string;
  label: string;
  snippet: string;
};

export function SourceEvidence({ sources }: { sources: CandidateSource[] }) {
  return (
    <section aria-labelledby="source-evidence-heading">
      <h3 id="source-evidence-heading">근거 원본</h3>
      {sources.map((source) => (
        <blockquote key={source.id}>
          <cite>{source.label}</cite>: {source.snippet}
        </blockquote>
      ))}
    </section>
  );
}
