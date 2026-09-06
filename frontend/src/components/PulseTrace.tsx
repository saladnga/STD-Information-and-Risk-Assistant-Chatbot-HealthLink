// The logo's heart-as-circuit motif, reused as a divider (static) or a
// chat "typing" signal (animated) instead of generic bouncing dots.
export default function PulseTrace({
  animated,
  className = "",
}: {
  animated?: boolean;
  className?: string;
}) {
  return (
    <svg
      viewBox="0 0 200 40"
      className={`text-troy-red ${animated ? "pulse-trace-animated" : ""} ${className}`}
    >
      <path
        d="M0,20 L76,20 L82,20 L88,4 L94,36 L100,20 L106,20 L112,10 L118,20 L200,20"
        fill="none"
        stroke="currentColor"
        strokeWidth="2"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}
