# Wobble — Motion-Controlled Audio & Light Installation

An interactive art installation where three physical "Wobbles" — wireless tilt controllers — are used to manipulate audio synthesis and Philips Hue lighting in real time through movement and proximity.

**Created by Joshua Pothen** as a thesis art installation.

---

## Overview

Wobble is a three-Wobble system. Each Wobble is a handheld object housing an ESP32-S3 microcontroller and a 6-axis IMU (accelerometer + gyroscope). Two Wobbles ("Receivers") scan for Bluetooth signal strength from a third ("Transmitter"), translating physical distance into proximity data. All motion and proximity data flows over WiFi via OSC to a Python middleware that orchestrates three interactive scenes, controlling both a VCV Rack audio patch and Philips Hue smart bulbs.

---

## System Architecture

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│  Receiver 1     │     │  Receiver 2     │     │  Transmitter    │
│  (Copper)       │     │  (White)        │     │  (Purple)       │
│                 │     │                 │     │                 │
│  ESP32-S3       │     │  ESP32-S3       │     │  ESP32-S3       │
│  LSM6DSOX       │     │  LSM6DSOX       │     │  LSM6DSOX       │
│  BLE Scanner    │◄────┼─────────────────┼────►│  BLE Beacon     │
└────────┬────────┘     └────────┬────────┘     └────────┬────────┘
         │                       │                       │
         │              WiFi / OSC                       │
         └───────────────────────┴───────────────────────┘
                                 │
                    ┌────────────▼────────────┐
                    │   Python Middleware      │
                    │   (wobble_unified_       │
                    │    processor.py)         │
                    └────────────┬────────────┘
                                 │
                 ┌───────────────┴───────────────┐
                 │                               │
          ┌──────▼──────┐                 ┌──────▼──────┐
          │  VCV Rack   │                 │  Hue Lights │
          │  (Audio)    │                 │  (OpenHue)  │
          └─────────────┘                 └─────────────┘
```

### Hardware

| Component | Part |
|-----------|------|
| Microcontroller | Adafruit QT Py ESP32-S3 × 3 |
| Motion sensor | Adafruit LSM6DSOX 6-DoF IMU × 3 |
| Proximity | BLE RSSI (built-in) |
| Lights | Philips Hue smart bulbs × 4 |

### Software

| Layer | Tool |
|-------|------|
| Firmware | Arduino (ESP32 BLE + WiFi) |
| Middleware | Python 3 with `python-osc` |
| Audio | VCV Rack (OSC receiver module) |
| Lighting | OpenHue CLI |
| Web dashboard | Next.js (Vercel) + Supabase |

---

## Repository Structure

```
Playful-Home/
├── README.md                    ← This file
├── INSTALLATION.md              ← Setup guide
├── INTERACTION_PATTERNS.md      ← Scene interaction reference
├── DEVELOPMENT_JOURNEY.md       ← Full development story
│
├── PlaytestV1/                  ← Active unified system
│   ├── wobble_unified_processor.py   ← Python middleware (main program)
│   ├── Transmitter_Purple.ino        ← Firmware: purple Wobble
│   ├── Receiver1_Copper.ino          ← Firmware: copper Wobble
│   ├── Receiver2_White.ino           ← Firmware: white Wobble
│   ├── supabase_schema.sql           ← Database schema
│   ├── config.json                   ← Threshold configuration
│   └── Backup/                       ← Backup board firmware
│       ├── Transmitter_Purple_B.ino
│       ├── Receiver1_Copper_B.ino
│       └── Receiver2_White_B.ino
│
└── wobble_dashboard/            ← Next.js web dashboard
    ├── app/                     ← Pages (live view + /trends)
    ├── components/              ← UI components
    ├── hooks/                   ← Data hooks (WebSocket + Supabase)
    └── lib/                     ← Supabase client + types
```

---

## The Three Scenes

### Scene 0 — Individual Layer Control
Each Wobble independently controls frequency and pitch of its own audio layer. Lights respond to proximity.

### Scene 1 — Distance-Based Multi-State
Distance from the Transmitter sets one of four room-wide light states (warm white / blue / cool white / red). Motion controls volume and decay in the audio patch.

### Scene 2 — Isolation Mode
Moving a Wobble beyond 0.8m "isolates" it: a random Hue bulb lights up a random color, and only that Wobble's motion drives the audio. Bringing it back deactivates isolation.

See [INTERACTION_PATTERNS.md](INTERACTION_PATTERNS.md) for full details.

---

## Quick Start

```bash
# 1. Flash each .ino to its corresponding ESP32-S3 board (one time only)

# 2. Install Python dependencies
pip install python-osc python-dotenv supabase

# 3. Run the middleware
cd PlaytestV1
python3 wobble_unified_processor.py
```

See [INSTALLATION.md](INSTALLATION.md) for complete setup instructions.

---

## Web Dashboard

A live Next.js dashboard shows Wobble states, session activity, and historical trends via Supabase.

```bash
cd wobble_dashboard
npm install
npm run dev
```

Requires `SUPABASE_URL`, `SUPABASE_ANON_KEY`, `SUPABASE_SERVICE_KEY` environment variables.

---

## Credits

**Hardware:** Adafruit QT Py ESP32-S3, Adafruit LSM6DSOX, Philips Hue
**Software:** Arduino ESP32 libraries, python-osc, OpenHue CLI, VCV Rack
**Created by:** Joshua Pothen
**License:** MIT
