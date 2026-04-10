'use client';

import { useWebSocketState } from '@/hooks/use-websocket-state';
import { ROCKERS } from '@/lib/constants';
import { Header } from './header';
import { ScenePanel } from './scene-panel';
import { RockerCard } from './rocker-card';
import { IntroOverlay } from './intro-overlay';

export function Dashboard() {
  const { state } = useWebSocketState();

  return (
    <div
      className="grid"
      style={{
        background: 'var(--bg)',
        minHeight: '100vh',
        gridTemplateRows: '48px auto 1fr',
      }}
    >
      <IntroOverlay />

      <Header state={state} />
      <ScenePanel state={state} />

      {/* Rocker cards */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 p-4 items-start">
        <RockerCard
          rockerKey="r1"
          name={ROCKERS.r1.label}
          color={ROCKERS.r1.color}
          live={state?.r1_live ?? false}
          source={state?.r1_source ?? 'primary'}
          isolated={state?.r1_isolated}
          accel={state?.r1_accel ?? [0, 0, 0]}
          gyro={state?.r1_gyro ?? [0, 0, 0]}
          distance={state?.r1_distance}
          sessionActive={state?.r1_session_active}
          sessionDuration={state?.r1_session_duration}
          wobbleEma={state?.r1_wobble_ema}
        />
        <RockerCard
          rockerKey="r2"
          name={ROCKERS.r2.label}
          color={ROCKERS.r2.color}
          live={state?.r2_live ?? false}
          source={state?.r2_source ?? 'primary'}
          isolated={state?.r2_isolated}
          accel={state?.r2_accel ?? [0, 0, 0]}
          gyro={state?.r2_gyro ?? [0, 0, 0]}
          distance={state?.r2_distance}
          sessionActive={state?.r2_session_active}
          sessionDuration={state?.r2_session_duration}
          wobbleEma={state?.r2_wobble_ema}
        />
        <RockerCard
          rockerKey="tx"
          name={ROCKERS.tx.label}
          color={ROCKERS.tx.color}
          live={state?.tx_live ?? false}
          source={state?.tx_source ?? 'primary'}
          accel={state?.tx_accel ?? [0, 0, 0]}
          gyro={state?.tx_gyro ?? [0, 0, 0]}
          sessionActive={state?.tx_session_active}
          sessionDuration={state?.tx_session_duration}
          wobbleEma={state?.tx_wobble_ema}
        />
      </div>
    </div>
  );
}
