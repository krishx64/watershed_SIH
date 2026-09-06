export default function CharReveal({
  text,
  startDelayMs = 0,
  staggerMs = 50,
  className,
}: {
  text: string;
  startDelayMs?: number;
  staggerMs?: number;
  className?: string;
}) {
  return (
    <span className={className}>
      {text.split("").map((char, i) => (
        <span
          key={i}
          className="animate-char-in inline-block"
          style={{ animationDelay: `${startDelayMs + i * staggerMs}ms` }}
        >
          {char === " " ? " " : char}
        </span>
      ))}
    </span>
  );
}
