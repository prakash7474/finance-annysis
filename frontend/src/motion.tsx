// motion-tokens + reusable motion primitives (Framer Motion + CSS fallbacks).

import { useEffect, useRef, useState } from "react";
import {
  AnimatePresence,
  motion,
  useReducedMotion,
  useSpring,
} from "framer-motion";

export const duration = {
  instant: 0.12,
  fast: 0.2,
  base: 0.35,
  slow: 0.6,
};

export const ease = {
  standard: [0.4, 0, 0.2, 1] as const,
  out: [0, 0, 0.2, 1] as const,
  in: [0.4, 0, 1, 1] as const,
  spring: { type: "spring" as const, stiffness: 300, damping: 24 },
};

export const stagger = { trace: 0.12, list: 0.05 };

export const useReduced = useReducedMotion;

// ── Entrances (fade + slide-up), respect reduced motion ─────────────────────
export function Reveal({
  children,
  delay = 0,
  className = "",
  y = 8,
}: {
  children: React.ReactNode;
  delay?: number;
  className?: string;
  y?: number;
}) {
  const reduce = useReducedMotion();
  return (
    <motion.div
      className={className}
      initial={reduce ? false : { opacity: 0, y }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: duration.base, ease: ease.out, delay }}
    >
      {children}
    </motion.div>
  );
}

export function Stagger({
  children,
  className = "",
  gap = stagger.list,
}: {
  children: React.ReactNode;
  className?: string;
  gap?: number;
}) {
  return (
    <motion.div
      className={className}
      initial="hidden"
      animate="show"
      variants={{ hidden: {}, show: { transition: { staggerChildren: gap } } }}
    >
      {children}
    </motion.div>
  );
}

export function RevealItem({
  children,
  className = "",
  y = 8,
}: {
  children: React.ReactNode;
  className?: string;
  y?: number;
}) {
  const reduce = useReducedMotion();
  return (
    <motion.div
      className={className}
      variants={{
        hidden: reduce ? { opacity: 0 } : { opacity: 0, y },
        show: { opacity: 1, y: 0, transition: { duration: duration.base, ease: ease.out } },
      }}
    >
      {children}
    </motion.div>
  );
}

// ── Animated number: spring count-up + optional value-change flash ───────────
export function AnimatedNumber({
  value,
  format = (v: number) => Math.round(v).toLocaleString("en-IN"),
  className = "",
  flash = false,
}: {
  value: number;
  format?: (v: number) => string;
  className?: string;
  flash?: boolean;
}) {
  const reduce = useReducedMotion();
  const mv = useSpring(0, { stiffness: 120, damping: 24 });
  const [disp, setDisp] = useState(0);
  const [tone, setTone] = useState<"mint" | "coral" | null>(null);
  const prev = useRef<number>(value);

  useEffect(() => {
    if (reduce) mv.jump(value);
    else mv.set(value);
  }, [value, reduce, mv]);
  useEffect(() => mv.on("change", (v: number) => setDisp(v)), [mv]);

  useEffect(() => {
    if (value !== prev.current) {
      setTone(value > prev.current ? "mint" : "coral");
      const id = setTimeout(() => setTone(null), 260);
      prev.current = value;
      return () => clearTimeout(id);
    }
  }, [value]);

  return (
    <span
      className={`${className} ${flash ? `num-flash ${tone ?? ""}` : ""}`}
      data-reduced-motion={reduce ? "true" : undefined}
    >
      {format(disp)}
    </span>
  );
}

// ── Pulse dot (loops while active, static otherwise) ────────────────────────
export function PulseDot({
  active,
  tone = "mint",
  size = 8,
}: {
  active?: boolean;
  tone?: string;
  size?: number;
}) {
  const color = tone === "coral" ? "var(--border-danger)" : tone === "amber" ? "#F5B942" : "#19C37D";
  return (
    <span
      className={`inline-block rounded-full ${active ? "motion-pulse" : ""}`}
      style={{ width: size, height: size, background: color, flex: "none" }}
      data-reduced-motion="true"
    />
  );
}

// ── Indeterminate scanning bar (thinking / connecting) ──────────────────────
export function ShimmerBar({ className = "" }: { className?: string }) {
  return (
    <span className={`shimmer-track ${className}`}>
      <span className="shimmer-bar" />
    </span>
  );
}

// ── Checkmark that draws in ─────────────────────────────────────────────────
export function Check({ size = 14 }: { size?: number }) {
  const reduce = useReducedMotion();
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" className="inline-block">
      <motion.path
        d="M4 12l5 5L20 6"
        stroke="currentColor"
        strokeWidth={2.6}
        strokeLinecap="round"
        strokeLinejoin="round"
        initial={{ pathLength: reduce ? 1 : 0 }}
        animate={{ pathLength: 1 }}
        transition={{ duration: duration.fast, ease: ease.out }}
      />
    </svg>
  );
}

// ── Sequential trace reveal (honors real order; reduced motion = instant) ────
export function TraceSteps({
  steps,
  className = "",
  gap = stagger.trace,
}: {
  steps: { label: string; tone?: "mint" | "coral" | "amber" }[];
  className?: string;
  gap?: number;
}) {
  const reduce = useReducedMotion();
  return (
    <motion.div
      className={className}
      initial={reduce ? false : "hidden"}
      animate="show"
      variants={{ hidden: {}, show: { transition: { staggerChildren: gap } } }}
    >
      {steps.map((s, i) => (
        <motion.div
          key={i}
          variants={
            reduce
              ? { hidden: { opacity: 0 }, show: { opacity: 1 } }
              : { hidden: { opacity: 0, y: 4 }, show: { opacity: 1, y: 0 } }
          }
          className="flex items-center gap-2 text-xs"
        >
          <span
            style={{
              color:
                s.tone === "coral" ? "var(--border-danger)" : s.tone === "amber" ? "#F5B942" : "var(--mint)",
            }}
          >
            ✓
          </span>
          {s.label}
        </motion.div>
      ))}
    </motion.div>
  );
}

// ── Toast (AnimatePresence) ─────────────────────────────────────────────────
export function Toast({
  show,
  tone = "coral",
  children,
  onDone,
}: {
  show: boolean;
  tone?: "coral" | "mint";
  children: React.ReactNode;
  onDone?: () => void;
}) {
  const reduce = useReducedMotion();
  return (
    <AnimatePresence>
      {show && (
        <motion.div
          key="toast"
          initial={reduce ? { opacity: 0 } : { opacity: 0, y: -24, scale: 0.96 }}
          animate={{ opacity: 1, y: 0, scale: 1 }}
          exit={reduce ? { opacity: 0 } : { opacity: 0, y: -12, scale: 0.96 }}
          transition={{ duration: duration.base, ease: ease.spring }}
          onAnimationComplete={onDone}
          className={`fixed top-4 right-4 z-50 rounded-xl border px-4 py-3 text-sm shadow-lg ${
            tone === "coral"
              ? "bg-[#1a0f12] border-[#3a1a20] text-[#ffd7d7]"
              : "bg-[#0f1a15] border-[#1a3a2a] text-[#d7ffe9]"
          }`}
        >
          {children}
        </motion.div>
      )}
    </AnimatePresence>
  );
}
