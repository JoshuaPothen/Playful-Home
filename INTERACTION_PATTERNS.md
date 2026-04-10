# Interaction Patterns

This document describes the three interactive scenes in the Wobble installation — what participants do and what the system responds with.

---

## The Objects

| Wobble | Color | Role |
|--------|-------|------|
| Transmitter | Purple | BLE beacon — stationary reference point |
| Receiver 1 | Copper | Interactive controller — scans BLE + reads motion |
| Receiver 2 | White | Interactive controller — scans BLE + reads motion |

All three Wobbles send 6-axis motion data (accelerometer + gyroscope) at ~25 Hz over WiFi. The two Receivers also report their BLE distance from the Transmitter.

---

## Scene 0 — Individual Layer Control

### What You Do
- Pick up Receiver 1 (Copper) and/or Receiver 2 (White) and move them freely.

### What Happens

**Audio:**
- Receiver 1 controls one layer of the audio track — tilting and rotating changes its frequency and pitch.
- Receiver 2 controls a separate audio layer in the same way.
- Each Wobble operates independently; moving both simultaneously creates harmonies.

**Lights:**
- Proximity to the Transmitter (Purple) changes the room light color:
  - Close (≤0.8 m) → warm white
  - Far (>0.8 m) → cool white

### In Plain Terms
> "Each Wobble is like a separate instrument. Moving one changes the sound of its own layer. Move both at the same time to create harmonies."

---

## Scene 1 — Distance-Based Multi-State

### What You Do
- Move the Wobbles closer to or farther from the Transmitter (Purple).
- Different distance combinations trigger different states.

### What Happens

**Lights (4 states based on distance from Transmitter):**

| State | Condition | Light Color |
|-------|-----------|-------------|
| Both close | Both ≤0.8 m | Warm white |
| Both far | Both ≥2.0 m | Red |
| Copper far, White close | R1 >0.8 m, R2 ≤0.8 m | Blue |
| White far, Copper close | R2 >0.8 m, R1 ≤0.8 m | Cool white |

**Audio:**
- Motion on every axis (X, Y, Z for accel and gyro) continuously controls volume and decay of different parts of the audio track.
- All sensor data is always forwarded to VCV Rack — the light states add spatial visual feedback on top.

### In Plain Terms
> "Your distance from the purple Wobble changes the room light color. Meanwhile, how you tilt and rotate the Wobbles controls the volume and echo of different parts of the music. It's like conducting an orchestra while the lights respond to where you're standing."

---

## Scene 2 — Isolation Mode

### What You Do
- Move a Wobble beyond 0.8 m from the Transmitter to "activate" it.
- Bring it back within 0.8 m to "deactivate" it.

### What Happens

**When Copper (Receiver 1) moves beyond 0.8 m:**
- One random Hue bulb changes to a random color and holds it.
- Only Copper's motion drives the audio — the other Wobble is muted.

**When White (Receiver 2) also moves beyond 0.8 m:**
- A *different* random bulb changes to a different random color.
- Both Wobbles are now isolated, each driving their own audio layer independently.

**When a Wobble returns within 0.8 m:**
- Its assigned bulb resets to warm white.
- Its audio isolation ends.
- The other Wobble (if still isolated) continues unaffected.

### Thresholds
- Isolation threshold: 0.8 m ± 0.15 m hysteresis
- Trigger cooldown: 1.5 s (prevents rapid toggling)

### In Plain Terms
> "Move a Wobble away to turn it on — one light changes color and that Wobble's sound gets isolated. Move the other Wobble away and another light changes color; now both sounds are isolated. Bring a Wobble back close to turn it off — its light goes back to white and its isolated sound stops. It's like individual on/off switches for each layer of music, with colored lights showing which ones are active."

---

## Hysteresis & Debouncing

All proximity thresholds include hysteresis (±0.15 m default) to prevent flickering at boundary distances. State changes are also debounced:

| Transition | Debounce |
|------------|---------|
| Scene 0 light change | 0.5 s |
| Scene 2 isolation trigger | 1.5 s |
| Scene 2 state change | 0.8 s |

Thresholds can be adjusted live via the Settings panel in the Python middleware GUI.

---

## Activity & Session Tracking

The system detects "wobble activity" using a combined accelerometer + gyroscope EMA signal. When activity crosses a threshold a session begins; when it stays below threshold for 60 seconds the session ends. Session data is persisted to Supabase and visible on the `/trends` page of the web dashboard.

| Metric | Description |
|--------|-------------|
| Wobble EMA | Exponential moving average of combined motion magnitude |
| Session active | Whether a Wobble is currently being actively moved |
| Session duration | Elapsed time since the current session started |
