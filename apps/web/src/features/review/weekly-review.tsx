export type WeekSummary = {
  plannedMinutes: number;
  actualMinutes: number;
  missedMinutes: number;
};

export function WeeklyReview({ week }: { week: WeekSummary }) {
  return (
    <section aria-label="주간 리뷰">
      <h1>주간 리뷰</h1>
      <p>{`계획 ${week.plannedMinutes}분 · 실제 ${week.actualMinutes}분`}</p>
      <p>{`미완료 ${week.missedMinutes}분은 다음 주로 이동합니다.`}</p>
    </section>
  );
}
