import { InboxList } from "../../../features/inbox/inbox-list";

export default function InboxPage() {
  return (
    <main>
      <h1>인박스</h1>
      <InboxList candidates={[]} />
    </main>
  );
}
