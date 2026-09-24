import { useEffect, useMemo, useState } from "react";
import { Shopping } from "../data/shoppings";

export interface SectorStatus {
  id: string;
  name: string;
  icon: string;
  total: number;
  free: number;
  spots: boolean[]; // true = free, false = occupied
}

function randomSpots(total: number): boolean[] {
  return Array.from({ length: total }, () => Math.random() > 0.62);
}

export function useParkingStatus(shopping: Shopping | undefined) {
  const [spotsBySector, setSpotsBySector] = useState<Record<string, boolean[]>>({});

  useEffect(() => {
    if (!shopping) return;
    const initial: Record<string, boolean[]> = {};
    shopping.sectors.forEach((s) => {
      initial[s.id] = randomSpots(s.total);
    });
    setSpotsBySector(initial);
  }, [shopping]);

  useEffect(() => {
    if (!shopping) return;
    const interval = setInterval(() => {
      setSpotsBySector((prev) => {
        const next = { ...prev };
        shopping.sectors.forEach((sector) => {
          const current = next[sector.id];
          if (!current) return;
          const updated = [...current];
          // flip a couple of random spots to simulate real-time movement
          const flips = Math.max(1, Math.floor(sector.total * 0.08));
          for (let i = 0; i < flips; i++) {
            const idx = Math.floor(Math.random() * updated.length);
            updated[idx] = !updated[idx];
          }
          next[sector.id] = updated;
        });
        return next;
      });
    }, 3500);
    return () => clearInterval(interval);
  }, [shopping]);

  const sectors: SectorStatus[] = useMemo(() => {
    if (!shopping) return [];
    return shopping.sectors.map((s) => {
      const spots = spotsBySector[s.id] ?? [];
      const free = spots.filter(Boolean).length;
      return { id: s.id, name: s.name, icon: s.icon, total: s.total, free, spots };
    });
  }, [shopping, spotsBySector]);

  const totals = useMemo(() => {
    const total = sectors.reduce((acc, s) => acc + s.total, 0);
    const free = sectors.reduce((acc, s) => acc + s.free, 0);
    const occupied = total - free;
    const occupancy = total > 0 ? Math.round((occupied / total) * 100) : 0;
    return { total, free, occupied, occupancy };
  }, [sectors]);

  return { sectors, totals };
}
