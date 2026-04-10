# Installation Guide

Complete setup guide for the Wobble interactive installation.

---

## Prerequisites

### Hardware Required
- 3× Adafruit QT Py ESP32-S3
- 3× Adafruit LSM6DSOX 6-DoF IMU (connected via I2C)
- 4× Philips Hue smart bulbs + Hue Bridge
- WiFi network (all boards and the host machine on the same network)

### Software Required
- [Arduino IDE](https://www.arduino.cc/en/software) with ESP32 board support
- Python 3.9+
- [VCV Rack](https://vcvrack.com/) with an OSC receiver module
- [OpenHue CLI](https://github.com/openhue/openhue-cli)
- Node.js 18+ (for web dashboard only)

---

## Step 1: Arduino Firmware

### Install Board Support
In Arduino IDE → Preferences → Additional Board Manager URLs, add:
```
https://raw.githubusercontent.com/espressif/arduino-esp32/gh-pages/package_esp32_index.json
```
Then install **esp32 by Espressif** via Board Manager.

### Install Libraries
In Library Manager, install:
- `ArduinoOSCWiFi` (or equivalent OSC over UDP library)
- `Adafruit LSM6DS`
- `Adafruit BusIO`
- `ESP32 BLE Arduino`

### Configure WiFi & IP
In each `.ino` file, update these values to match your network:
```cpp
const char* ssid = "YourNetworkName";
const char* password = "YourPassword";
IPAddress host(192, 168, X, X);  // IP of the machine running Python
```

### Flash Each Board
| Board | File |
|-------|------|
| Purple Wobble (Transmitter) | `PlaytestV1/Transmitter_Purple.ino` |
| Copper Wobble (Receiver 1) | `PlaytestV1/Receiver1_Copper.ino` |
| White Wobble (Receiver 2) | `PlaytestV1/Receiver2_White.ino` |

Select **Adafruit QT Py ESP32-S3** as the board before uploading.

> **Backup boards:** If you have secondary/backup hardware, use the `.ino` files in `PlaytestV1/Backup/`.

---

## Step 2: Python Middleware

### Install Dependencies
```bash
pip install python-osc python-dotenv supabase
```

### Configure Hue Lights
1. Install OpenHue CLI and connect it to your Hue Bridge (follow [OpenHue docs](https://github.com/openhue/openhue-cli)).
2. Find your bulb IDs with `openhue get lights`.
3. Open `PlaytestV1/wobble_unified_processor.py` and update:

```python
HUE_LIGHTS = [
    {"id": "your-bulb-id-1", "name": "Lamp 1"},
    {"id": "your-bulb-id-2", "name": "Lamp 2"},
    {"id": "your-bulb-id-3", "name": "Light 3"},
    {"id": "your-bulb-id-4", "name": "Essential 2"},
]
HUE_ROOM_ID = "your-room-id"
```

### Configure Supabase (Optional — for session tracking)
Create a `.env` file in `PlaytestV1/`:
```
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_SERVICE_KEY=your-service-key
```

Apply the schema:
```bash
# Run in Supabase SQL editor or via psql
cat PlaytestV1/supabase_schema.sql
```

### Run
```bash
cd PlaytestV1
python3 wobble_unified_processor.py
```

A Tkinter GUI will appear with scene buttons, a live dashboard, and an event log.

---

## Step 3: VCV Rack

1. Open VCV Rack and load or create a patch.
2. Add an OSC receiver module and configure it to listen on:
   - **Port 8010** — Scene 1 & 2 sensor data
   - **Port 8011** — Scene 0 sensor data
3. Map the incoming OSC addresses:

| Address | Scene | Description |
|---------|-------|-------------|
| `/r1/accel/x,y,z` | 1 & 2 | Receiver 1 accelerometer |
| `/r1/gyro/x,y,z` | 1 & 2 | Receiver 1 gyroscope |
| `/r2/accel/x,y,z` | 1 & 2 | Receiver 2 accelerometer |
| `/r2/gyro/x,y,z` | 1 & 2 | Receiver 2 gyroscope |
| `/s0/r1/accel/x,y,z` | 0 | Scene 0 Receiver 1 accel |
| `/s0/r1/gyro/x,y,z` | 0 | Scene 0 Receiver 1 gyro |
| `/s0/mute` | 0 | 1 = Scene 0 active |
| `/s2/r1/mute` | 2 | 1 = Receiver 1 isolated |
| `/s2/r2/mute` | 2 | 1 = Receiver 2 isolated |

---

## Step 4: Web Dashboard (Optional)

```bash
cd wobble_dashboard
npm install
```

Create `.env.local`:
```
NEXT_PUBLIC_SUPABASE_URL=https://your-project.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=your-anon-key
```

```bash
npm run dev
# Open http://localhost:3000
```

The dashboard connects to the Python middleware via WebSocket and displays live Wobble states, session activity, and historical trends.

---

## Threshold Configuration

Proximity thresholds can be tuned from the GUI's **Settings** panel without restarting:

| Setting | Default | Description |
|---------|---------|-------------|
| Close threshold | 0.8 m | Distance below which a Wobble is "close" |
| Far threshold | 2.0 m | Distance above which a Wobble is "far" (Scene 1) |
| Hysteresis | 0.15 m | Buffer to prevent threshold flickering |

Settings are saved to `PlaytestV1/config.json` via the **Save** button.

---

## OSC Port Reference

| Port | Direction | Source/Destination |
|------|-----------|-------------------|
| 8001 | IN | Receiver 1 (Copper) — proximity |
| 8002 | IN | Receiver 2 (White) — proximity |
| 8004 | IN | Receiver 1 (Copper) — sensors |
| 8005 | IN | Transmitter (Purple) — sensors |
| 8006 | IN | Receiver 2 (White) — sensors |
| 8010 | OUT | Python → VCV Rack (Scene 1 & 2) |
| 8011 | OUT | Python → VCV Rack (Scene 0) |

Backup board ports follow the same pattern on 8101/8102/8104/8105/8106.

---

## Troubleshooting

**No OSC data received**
- Open Arduino Serial Monitor — check that the board shows WiFi connected and is sending to the correct IP.
- Verify the laptop's IP matches what's hardcoded in the `.ino` files.

**Lights not changing**
- Run `openhue --version` to confirm OpenHue is installed.
- Run `openhue get lights` to verify bulb IDs match the Python config.

**GUI doesn't appear**
- macOS: `brew install python-tk`
- Or run with system Python: `/usr/bin/python3 wobble_unified_processor.py`

**Distance detection erratic**
- BLE RSSI varies with orientation and obstacles. Increase hysteresis in the Settings panel.
- Keep the Transmitter (purple) stationary during calibration.

**VCV Rack not receiving data**
- Check firewall isn't blocking UDP ports 8010/8011.
- Confirm the OSC receiver module is set to the correct port.
