"use client";

import { useEffect, useRef } from "react";

const CHARSET = ["▲", "◎", "~", "≈", "+", "×", "0", "N", "S", "E", "W", "⊕"];
const PARTICLE_COUNT = 400;
const BASE_COLOR = "78, 122, 61"; // sage, rgb components

type Particle = {
  x: number;
  y: number;
  char: string;
  size: number;
  baseOpacity: number;
  driftX: number;
  driftY: number;
  angle: number;
};

export default function HeroCanvas() {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const mouseRef = useRef({ x: -9999, y: -9999 });

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    let width = 0;
    let height = 0;
    let particles: Particle[] = [];
    let raf = 0;

    function resize() {
      if (!canvas) return;
      const parent = canvas.parentElement;
      width = parent?.clientWidth ?? window.innerWidth;
      height = parent?.clientHeight ?? window.innerHeight;
      canvas.width = width * devicePixelRatio;
      canvas.height = height * devicePixelRatio;
      canvas.style.width = `${width}px`;
      canvas.style.height = `${height}px`;
      ctx?.scale(devicePixelRatio, devicePixelRatio);

      particles = Array.from({ length: PARTICLE_COUNT }, () => ({
        x: Math.random() * width,
        y: Math.random() * height,
        char: CHARSET[Math.floor(Math.random() * CHARSET.length)],
        size: 8 + Math.random() * 4,
        baseOpacity: 0.1 + Math.random() * 0.3,
        driftX: (Math.random() - 0.5) * 0.15,
        driftY: (Math.random() - 0.5) * 0.15,
        angle: 0,
      }));
    }

    function onMouseMove(e: MouseEvent) {
      const rect = canvas!.getBoundingClientRect();
      mouseRef.current = { x: e.clientX - rect.left, y: e.clientY - rect.top };
    }
    function onMouseLeave() {
      mouseRef.current = { x: -9999, y: -9999 };
    }

    function tick() {
      if (!ctx) return;
      ctx.clearRect(0, 0, width, height);
      const { x: mx, y: my } = mouseRef.current;

      for (const p of particles) {
        p.x += p.driftX;
        p.y += p.driftY;
        if (p.x < 0) p.x = width;
        if (p.x > width) p.x = 0;
        if (p.y < 0) p.y = height;
        if (p.y > height) p.y = 0;

        const dx = p.x - mx;
        const dy = p.y - my;
        const dist = Math.sqrt(dx * dx + dy * dy);
        const proximity = Math.max(0, 1 - dist / 140);
        const opacity = Math.min(0.9, p.baseOpacity + proximity * 0.6);
        const repel = proximity * 6;
        const drawX = dist > 0.001 ? p.x + (dx / (dist || 1)) * repel : p.x;
        const drawY = dist > 0.001 ? p.y + (dy / (dist || 1)) * repel : p.y;

        ctx.font = `${p.size}px var(--font-mono, monospace)`;
        ctx.fillStyle = `rgba(${BASE_COLOR}, ${opacity})`;
        ctx.fillText(p.char, drawX, drawY);
      }
      raf = requestAnimationFrame(tick);
    }

    resize();
    window.addEventListener("resize", resize);
    canvas.addEventListener("mousemove", onMouseMove);
    canvas.addEventListener("mouseleave", onMouseLeave);
    raf = requestAnimationFrame(tick);

    return () => {
      cancelAnimationFrame(raf);
      window.removeEventListener("resize", resize);
      canvas.removeEventListener("mousemove", onMouseMove);
      canvas.removeEventListener("mouseleave", onMouseLeave);
    };
  }, []);

  return <canvas ref={canvasRef} className="absolute inset-0 h-full w-full" aria-hidden />;
}
