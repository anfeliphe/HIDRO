/**
 * Map marker color by daily consumption (API values in liters; labels shown in m³).
 * Used for parcel markers; thresholds are illustrative.
 */
export const CONSUMPTION_THRESHOLDS_L = { low: 500, medium: 800, high: 1100 };

export function getConsumptionLevel(daily) {
  if (daily < 500) return { level: "Baja", color: '#93c5fd', threshold: '< 0.5 m³' };
  if (daily < 800) return { level: "Media", color: '#60a5fa', threshold: '0.5–0.8 m³' };
  if (daily < 1100) return { level: "Alta", color: '#3b82f6', threshold: '0.8–1.1 m³' };
  return { level: "Crítica", color: '#1e40af', threshold: '> 1.1 m³' };
}
