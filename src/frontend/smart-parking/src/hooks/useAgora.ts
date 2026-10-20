import { useEffect, useState } from "react";

/**
 * Ticker para selos "ao vivo" e "atualizado há Xs" — 1s no app.
 */
export function useAgora(intervaloMs = 1000): number {
  const [agora, setAgora] = useState(Date.now());
  useEffect(() => {
    const t = setInterval(() => setAgora(Date.now()), intervaloMs);
    return () => clearInterval(t);
  }, [intervaloMs]);
  return agora;
}

export function desdeAte(labelMs: number, agora: number): string {
  const s = Math.max(0, Math.round((agora - labelMs) / 1000));
  if (s < 5) return "agora mesmo";
  if (s < 60) return `há ${s}s`;
  const m = Math.floor(s / 60);
  if (m < 60) return `há ${m} min`;
  return `há ${Math.floor(m / 60)}h`;
}
