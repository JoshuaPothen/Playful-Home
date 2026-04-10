import { clsx, type ClassValue } from 'clsx';
import { twMerge } from 'tailwind-merge';
import { HUE_COLORS } from './constants';

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export function resolveHue(colorName: string): string {
  if (!colorName) return HUE_COLORS['off'];
  const key = colorName.toLowerCase().replace(/\s+/g, '_');
  return HUE_COLORS[key] ?? HUE_COLORS['warm_white'];
}

export function gyroMag(gyro: [number, number, number]): number {
  const [x, y, z] = gyro;
  return Math.sqrt(x * x + y * y + z * z);
}

export function formatDist(dist: number | undefined | null): string {
  if (dist === undefined || dist === null || isNaN(dist)) return '—';
  return `${dist.toFixed(2)}m`;
}
