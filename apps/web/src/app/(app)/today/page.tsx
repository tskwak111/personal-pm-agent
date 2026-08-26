import { TodayView, type TodayPlan } from "../../../features/today/today-view";

const emptyPlan: TodayPlan = {
  coreOutcome: "",
  selectionReason: "",
  fixedEvents: [],
  mustDo: [],
  queue: [],
  notToday: [],
};

export default function TodayPage() {
  return <TodayView plan={emptyPlan} />;
}
