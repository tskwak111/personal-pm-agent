export default async function ProjectDetailPage({
  params,
}: {
  params: Promise<{ workstreamId: string }>;
}) {
  const { workstreamId } = await params;
  return (
    <main>
      <h1>프로젝트 {workstreamId}</h1>
    </main>
  );
}
