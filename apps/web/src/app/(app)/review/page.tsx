import { WeeklyReview } from "../../../features/review/weekly-review";

export default function ReviewPage() {
  return <WeeklyReview week={{ plannedMinutes: 0, actualMinutes: 0, missedMinutes: 0 }} />;
}
