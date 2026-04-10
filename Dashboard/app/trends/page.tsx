'use client';

import dynamic from 'next/dynamic';

const TrendDashboard = dynamic(
  () => import('@/components/trends/trend-dashboard').then((m) => m.TrendDashboard),
  { ssr: false }
);

export default function TrendsPage() {
  return <TrendDashboard />;
}
