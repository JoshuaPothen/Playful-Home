import Link from 'next/link';
import { ROCKERS } from '@/lib/constants';

export default function AboutPage() {
  const wobbles = Object.values(ROCKERS);

  return (
    <div className="min-h-screen" style={{ background: 'var(--bg)' }}>
      {/* Header */}
      <header
        className="sticky top-0 z-40 flex items-center justify-between px-4 sm:px-6 h-12 sm:h-16 border-b border-[var(--border)]"
        style={{ background: 'var(--bg)' }}
      >
        <Link
          href="/"
          className="font-semibold tracking-[0.42em] text-sm sm:text-[18px] text-zinc-100 hover:text-white transition-colors"
        >
          PLAYFUL HOME
        </Link>
        <div className="flex items-center gap-6">
          <Link
            href="/trends"
            className="text-sm sm:text-[18px] text-zinc-500 tracking-[0.3em] uppercase hover:text-zinc-300 transition-colors"
          >
            TRENDS
          </Link>
          <span className="text-sm sm:text-[18px] text-zinc-300 tracking-[0.3em] uppercase">
            ABOUT
          </span>
        </div>
      </header>

      <main className="max-w-2xl mx-auto px-6 py-16 flex flex-col gap-14">

        {/* Intro */}
        <section className="flex flex-col gap-6">
          <h1 className="text-2xl sm:text-3xl font-semibold text-zinc-100 tracking-wide">
            Playful Home
          </h1>
          <p className="text-zinc-400 leading-relaxed">
            Playful Home is an ecosystem that utilises domestic space as a site for creative
            engagement. Rather than replacing existing infrastructure, it acts as an interaction
            layer that leverages standard smart home systems. While contemporary smart homes focus
            on utility through automated thermostats and functional lighting, this project
            challenges the functionality paradigm by prioritising the playfulness of interaction
            over the efficiency of the outcome.
          </p>
          <p className="text-zinc-400 leading-relaxed">
            Wobbles serve as the primary tool for developing Playful Home — a collection of
            wireless tangible interfaces that convert physical gestures such as tilting, spinning,
            or moving into expressive digital data streams. Designed as seemingly unassuming
            objects for domestic spaces, they bridge the gap between physical input and digital
            response, allowing users to affect their ambient media by controlling generative
            soundscapes in VCV Rack and adjusting environmental lighting via Philips Hue bulbs.
          </p>
          <p className="text-zinc-400 leading-relaxed">
            The result is a playfully engaging environment where Wobbles co-exist within the home
            as expressive tools that encourage an open-ended, exploratory relationship with the
            space we inhabit.
          </p>
        </section>

        {/* The Wobbles */}
        <section className="flex flex-col gap-6">
          <h2 className="text-xs tracking-[0.3em] text-zinc-500 uppercase">The Wobbles</h2>
          <div className="flex flex-col gap-5">
            <div className="flex items-start gap-4">
              <div
                className="w-3 h-3 rounded-full shrink-0 mt-1"
                style={{ background: ROCKERS.tx.color, boxShadow: `0 0 8px ${ROCKERS.tx.color}88` }}
              />
              <div className="flex flex-col gap-1">
                <span className="text-sm font-semibold tracking-widest" style={{ color: ROCKERS.tx.color }}>
                  PURPLE — Transmitter
                </span>
                <p className="text-zinc-400 text-sm leading-relaxed">
                  The reference point of the installation. Broadcasts a BLE signal that the other
                  two wobbles use to measure their distance. Its own motion data is sent directly
                  to the audio system.
                </p>
              </div>
            </div>
            <div className="flex items-start gap-4">
              <div
                className="w-3 h-3 rounded-full shrink-0 mt-1"
                style={{ background: ROCKERS.r1.color, boxShadow: `0 0 8px ${ROCKERS.r1.color}88` }}
              />
              <div className="flex flex-col gap-1">
                <span className="text-sm font-semibold tracking-widest" style={{ color: ROCKERS.r1.color }}>
                  COPPER — Receiver 1
                </span>
                <p className="text-zinc-400 text-sm leading-relaxed">
                  Detects its distance from Purple via BLE signal strength. Sends tilt and rotation
                  data to control one layer of audio, and triggers lighting changes based on
                  proximity.
                </p>
              </div>
            </div>
            <div className="flex items-start gap-4">
              <div
                className="w-3 h-3 rounded-full shrink-0 mt-1"
                style={{ background: ROCKERS.r2.color, boxShadow: `0 0 8px ${ROCKERS.r2.color}88` }}
              />
              <div className="flex flex-col gap-1">
                <span className="text-sm font-semibold tracking-widest" style={{ color: ROCKERS.r2.color }}>
                  WHITE — Receiver 2
                </span>
                <p className="text-zinc-400 text-sm leading-relaxed">
                  Works the same as Copper — independent distance sensing from Purple and its own
                  audio layer — allowing two performers to interact simultaneously or in unison.
                </p>
              </div>
            </div>
          </div>
        </section>

        {/* Scenes */}
        <section className="flex flex-col gap-4">
          <h2 className="text-xs tracking-[0.3em] text-zinc-500 uppercase">Scenes</h2>
          <p className="text-zinc-400 text-sm leading-relaxed">
            Three interaction configurations explore different relationships between gesture,
            proximity, and environmental response. They share the same hardware but define their
            output differently in software, switchable in real-time via a GUI. Together they
            constitute an interaction vocabulary from simple to complex and open-ended.
          </p>
        </section>

        <section className="flex flex-col gap-8">
          {/* Scene 0 */}
          <div className="flex flex-col gap-3">
            <div className="flex items-center gap-3">
              <span className="text-yellow-300 font-mono text-xs">00</span>
              <h3 className="text-zinc-200 font-medium tracking-wide">Individual Layers</h3>
            </div>
            <p className="text-zinc-400 text-sm leading-relaxed">
              Two Wobbles control the room&apos;s soundscape through a direct 1:1 gesture mapping —
              X-axis controls pitch, Y-axis tilt controls frequency. The sound output is minimal
              and ambient, designed for legibility. Participants can establish within a few seconds
              that the object responds to them rather than acting autonomously.
            </p>
            <p className="text-zinc-400 text-sm leading-relaxed">
              Lighting follows a single proximity threshold: when the Wobbles are close to each
              other the lights are set to warm white; when they are far apart, cool white.
            </p>
          </div>

          <div className="border-t border-[var(--border)]" />

          {/* Scene 1 */}
          <div className="flex flex-col gap-3">
            <div className="flex items-center gap-3">
              <span className="text-sky-300 font-mono text-xs">01</span>
              <h3 className="text-zinc-200 font-medium tracking-wide">Distance States</h3>
            </div>
            <p className="text-zinc-400 text-sm leading-relaxed">
              All three Wobbles operate simultaneously — one transmitter and two receivers. Their
              relative positions trigger four distinct lighting states, while motion data is mapped
              to volume and decay in the synthesis patch. Participants negotiate the room&apos;s
              lighting state through spatial positioning, shifting the interaction from a simple
              one-to-one mapping to a more complex networked system.
            </p>
            <ul className="flex flex-col gap-2 text-sm mt-1">
              <li className="flex gap-3">
                <span className="w-2 h-2 rounded-full bg-amber-200 shrink-0 mt-1.5" />
                <span className="text-zinc-400"><span className="text-zinc-300">All close — </span>warm white.</span>
              </li>
              <li className="flex gap-3">
                <span className="w-2 h-2 rounded-full bg-blue-400 shrink-0 mt-1.5" />
                <span className="text-zinc-400"><span className="text-zinc-300">Only Copper far — </span>blue.</span>
              </li>
              <li className="flex gap-3">
                <span className="w-2 h-2 rounded-full bg-sky-200 shrink-0 mt-1.5" />
                <span className="text-zinc-400"><span className="text-zinc-300">Only White far — </span>cool white.</span>
              </li>
              <li className="flex gap-3">
                <span className="w-2 h-2 rounded-full bg-red-500 shrink-0 mt-1.5" />
                <span className="text-zinc-400"><span className="text-zinc-300">All separate — </span>red.</span>
              </li>
            </ul>
          </div>

          <div className="border-t border-[var(--border)]" />

          {/* Scene 2 */}
          <div className="flex flex-col gap-3">
            <div className="flex items-center gap-3">
              <span className="text-purple-400 font-mono text-xs">02</span>
              <h3 className="text-zinc-200 font-medium tracking-wide">Isolation Mode</h3>
            </div>
            <p className="text-zinc-400 text-sm leading-relaxed">
              Moving a Wobble beyond the 0.8 m threshold activates it — a random Hue bulb changes
              to a randomly selected colour from a curated palette. This randomness is deliberate:
              a predictable mapping can be decoded and mastered, but a random one resists that
              process, sustaining an exploratory mode where participants remain in a state of
              curiosity and play rather than shifting into task completion.
            </p>
            <p className="text-zinc-400 text-sm leading-relaxed">
              The randomness doesn&apos;t make the system feel broken — it makes it feel generative.
              Bringing a Wobble back within range resets its bulb and removes it from isolation.
            </p>
          </div>
        </section>

        {/* Tech */}
        <section className="flex flex-col gap-4">
          <h2 className="text-xs tracking-[0.3em] text-zinc-500 uppercase">Tech Stack</h2>
          <ul className="flex flex-col gap-2 text-sm text-zinc-400">
            <li><span className="text-zinc-200">Hardware — </span>Adafruit QT Py ESP32-S3 with LSM6DSOX 6-axis IMU, BLE + WiFi</li>
            <li><span className="text-zinc-200">Audio — </span>VCV Rack (modular synthesis), controlled via OSC over WiFi</li>
            <li><span className="text-zinc-200">Lighting — </span>Philips Hue via OpenHue CLI</li>
            <li><span className="text-zinc-200">Backend — </span>Python processor managing scene logic and routing</li>
            <li><span className="text-zinc-200">Dashboard — </span>Next.js, Tailwind CSS, WebSocket, Supabase</li>
          </ul>
        </section>

        {/* Creator */}
        <section className="flex flex-col gap-4 border-t border-[var(--border)] pt-10">
          <h2 className="text-xs tracking-[0.3em] text-zinc-500 uppercase">Creator</h2>
          <p className="text-zinc-400 leading-relaxed">
            Designed and built by{' '}
            <span className="text-zinc-100 font-medium">Joshua Jacob Pothen</span>.
          </p>
          <a
            href="https://joshuapothen.com"
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex items-center gap-2 self-start px-4 py-2 text-sm tracking-widest uppercase border border-zinc-700 text-zinc-300 hover:border-zinc-400 hover:text-zinc-100 transition-colors"
          >
            joshuapothen.com
          </a>
        </section>

      </main>
    </div>
  );
}
