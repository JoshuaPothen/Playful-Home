# Wobble: Complete Development Journey
## From Concept to Interactive Installation

*A comprehensive documentation of the design, development, challenges, and evolution of the Wobble motion-controlled audio-visual system*

---

## Table of Contents

1. [Project Genesis](#project-genesis)
2. [System Architecture Overview](#system-architecture-overview)
3. [Phase 1: Initial Prototype (Reference Implementation)](#phase-1-initial-prototype)
4. [Phase 2: Scene 0 - Individual Layer Control](#phase-2-scene-0)
5. [Phase 3: Scene 1 - Distance-Based Multi-State](#phase-3-scene-1)
6. [Phase 4: Scene 2 - Isolation Mode](#phase-4-scene-2)
7. [Phase 5: Unified System (PlaytestV1)](#phase-5-unified-system)
8. [Technical Challenges & Solutions](#technical-challenges--solutions)
9. [Debug Tools & Monitoring](#debug-tools--monitoring)
10. [Lessons Learned](#lessons-learned)
11. [Future Development](#future-development)

---

## Project Genesis

### Concept
The Wobble project emerged from the intersection of three core ideas:
1. **Physical Computing** - Using motion sensors to create tangible interfaces
2. **Spatial Interaction** - Leveraging proximity and distance as control parameters
3. **Audio-Visual Synthesis** - Creating synchronized experiences across light and sound

### Initial Vision
Create an interactive installation where physical "rockers" (tilting controllers with motion sensors) would allow performers to:
- Control audio synthesis through movement
- Manipulate room lighting based on spatial relationships
- Create emergent behaviors through multi-rocker interactions

### Hardware Selection

**Microcontroller: Adafruit QT Py ESP32-S3**
- ✅ Dual-core processor (multitasking for BLE + WiFi)
- ✅ Built-in WiFi for OSC communication
- ✅ Bluetooth Low Energy for proximity detection
- ✅ Small form factor for embedded "rocker" design
- ✅ I2C support for sensor communication

**Sensor: LSM6DSOX (6-axis IMU)**
- ✅ Combined accelerometer + gyroscope
- ✅ High sample rate (104Hz) for responsive motion detection
- ✅ Low power consumption
- ✅ I2C communication
- ✅ Configurable ranges

**Smart Lighting: Philips Hue**
- ✅ Rich color control (140+ named colors)
- ✅ API access via OpenHue CLI
- ✅ Room-level and individual bulb control
- ✅ Smooth transitions

---

## System Architecture Overview

### High-Level Architecture

```
┌────────────────────────────────────────────────────────────────────┐
│                        WOBBLE SYSTEM                               │
└────────────────────────────────────────────────────────────────────┘

┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│  Receiver 1     │     │  Receiver 2     │     │  Transmitter    │
│  (Copper)       │     │  (White)        │     │  (Purple)       │
│                 │     │                 │     │                 │
│  ESP32-S3       │     │  ESP32-S3       │     │  ESP32-S3       │
│  LSM6DSOX       │     │  LSM6DSOX       │     │  LSM6DSOX       │
│  BLE Scanner    │     │  BLE Scanner    │     │  BLE Beacon     │
└────────┬────────┘     └────────┬────────┘     └────────┬────────┘
         │                       │                       │
         │ WiFi OSC              │ WiFi OSC              │ WiFi OSC
         │ Ports: 8001, 8004     │ Ports: 8002, 8006     │ Port: 8005
         │                       │                       │
         └───────────────────────┴───────────────────────┘
                                 │
                      ┌──────────▼──────────┐
                      │  Python Processor   │
                      │  Scene Controller   │
                      └──────────┬──────────┘
                                 │
                 ┌───────────────┴───────────────┐
                 │                               │
          ┌──────▼──────┐                 ┌──────▼──────┐
          │  VCV Rack   │                 │  Hue Lights │
          │  Audio      │                 │  OpenHue    │
          │  Port 8010  │                 │  CLI        │
          │  Port 8011  │                 │             │
          └─────────────┘                 └─────────────┘
```

### Communication Flow

```
[Hardware Layer]
    ↓ I2C (104Hz sensor sampling)
[Firmware Layer]
    ↓ WiFi UDP (OSC messages, ~25Hz)
[Middleware Layer - Python]
    ↓ OSC (sensor data) + CLI (light commands)
[Output Layer]
    → VCV Rack (audio synthesis)
    → Hue Bridge (lighting control)
```

---

## Phase 1: Initial Prototype (Reference Implementation)

### Objective
Establish basic hardware-software communication and validate the concept with two rockers.

### Implementation

**Hardware Setup:**
- 2x ESP32-S3 boards
- 2x LSM6DSOX sensors
- BLE proximity detection between boards
- WiFi connectivity to laptop

**Software Stack:**
```
Reference/
├── Transmitter_BLE_LSM6.ino  # Purple rocker - BLE beacon
├── Receiver_BLE_LSM6.ino     # Copper rocker - BLE scanner + proximity
└── osc_hue_control.py        # Python middleware
```

### Architecture Diagram - Phase 1

```
┌─────────────────────────────┐
│   Rocker 1 (Purple)         │
│   - LSM6DSOX Sensor         │
│   - BLE Beacon (max power)  │
│   - WiFi OSC → Port 8005    │
│     /accel/x,y,z            │
│     /gyro/x,y,z             │
└──────────────┬──────────────┘
               │ BLE Signal (RSSI)
               ↓
┌──────────────────────────────┐
│   Rocker 2 (Copper)          │
│   - LSM6DSOX Sensor          │
│   - BLE Scanner              │
│   - RSSI Distance Calc       │
│   - WiFi OSC → Port 8004     │
│     /accel/x,y,z             │
│     /gyro/x,y,z              │
│   - WiFi OSC → Port 8001     │
│     /weeble_proximity (0/1)  │
└──────────────┬───────────────┘
               │
               ↓
┌──────────────────────────────┐
│   Python: osc_hue_control.py │
│   - Listen: Port 8001        │
│   - Process proximity events │
│   - Control Hue lights       │
└──────────────┬───────────────┘
               │
               ↓
┌──────────────────────────────┐
│   OpenHue CLI                │
│   - Room control             │
│   - Color: Blue (close)      │
│   - Color: Red (far)         │
└──────────────────────────────┘
```

### Key Features
1. **Proximity Detection**: RSSI-based distance calculation
2. **Binary States**: Close (<40cm) vs Far (>40cm)
3. **Light Control**: Blue when close, Red when far
4. **Sensor Streaming**: Raw accelerometer/gyroscope data to VCV Rack

### Challenges Encountered

#### Challenge 1: RSSI Instability
**Problem:** RSSI values fluctuated wildly (-30dBm to -90dBm), causing rapid state changes.

**Solution:**
```cpp
// Implemented rolling average smoothing
#define RSSI_SAMPLES 5
int rssiBuffer[RSSI_SAMPLES];
int rssiIndex = 0;

int smoothedRSSI = 0;
for(int i = 0; i < RSSI_SAMPLES; i++) {
    smoothedRSSI += rssiBuffer[i];
}
smoothedRSSI /= RSSI_SAMPLES;
```

**Result:** ✅ Stable proximity detection with ~2-3 second smoothing window

#### Challenge 2: WiFi-BLE Interference
**Problem:** WiFi and BLE operations on same ESP32 caused connection drops.

**Solution:** Dual-core separation
```cpp
void setup() {
    // Core 0: BLE operations
    xTaskCreatePinnedToCore(
        bleTask, "BLE Task", 10000, NULL, 1, NULL, 0
    );
    
    // Core 1: WiFi + Sensors + OSC
    // Main loop handles WiFi operations
}
```

**Result:** ✅ Stable concurrent operations, no connection drops

#### Challenge 3: Sensor Data Rate Overload
**Problem:** Sending sensor data at 104Hz saturated network bandwidth.

**Solution:** Throttle OSC transmission
```cpp
#define SENSOR_UPDATE_INTERVAL 40  // 25Hz = every 40ms
unsigned long lastSensorSendTime = 0;

if (currentTime - lastSensorSendTime >= SENSOR_UPDATE_INTERVAL) {
    sendSensorBundle();
    lastSensorSendTime = currentTime;
}
```

**Result:** ✅ Responsive control without network congestion

### Success Metrics
- ✅ Reliable BLE proximity detection
- ✅ Consistent sensor data streaming
- ✅ Synchronized light control
- ✅ Proof of concept validated

### Debug Tools - Phase 1

**Arduino Serial Monitor:**
```
Wobble Reference System - Receiver (Copper)
==========================================
WiFi connected: 192.168.50.100
BLE Scanner active
Sensor: LSM6DSOX initialized

[Loop] RSSI: -65 | Distance: 0.35m | State: CLOSE
[OSC] Sent proximity: 1 (close)
[Hue] Command: Blue
Accel: X=1.23 Y=-0.45 Z=9.81 | Gyro: X=0.01 Y=-0.02 Z=0.00

[Loop] RSSI: -72 | Distance: 0.52m | State: FAR
[OSC] Sent proximity: 0 (far)
[Hue] Command: Red
```

---

## Phase 2: Scene 0 - Individual Layer Control

### Objective
Create a scene where each rocker independently controls audio layers, with proximity affecting light temperature.

### Design Goals
1. R1 (Copper) controls Layer 1 audio parameters
2. Transmitter (Purple) acts as proximity reference
3. Proximity changes light temperature (warm ↔ cool)
4. No interaction between R1 and R2 (White not used)

### Architecture Diagram - Scene 0

```
┌─────────────────────────────────────────────────────────────────┐
│                          SCENE 0                                │
│                   Individual Layer Control                      │
└─────────────────────────────────────────────────────────────────┘

┌──────────────────┐                    ┌──────────────────┐
│  R1 (Copper)     │                    │  Transmitter     │
│                  │                    │  (Purple)        │
│  Motion Sensor   │  BLE Proximity     │  BLE Beacon      │
│  OSC: 8004       │◄───────────────────│  Motion Sensor   │
│  Proximity: 8001 │    RSSI Distance   │  OSC: 8005       │
└────────┬─────────┘                    └────────┬─────────┘
         │                                       │
         │ Sensor Data                           │ Sensor Data
         └───────────────┬───────────────────────┘
                         │
                  ┌──────▼──────────┐
                  │ Scene 0 Python  │
                  │                 │
                  │ Port 8011 (VCV) │
                  │ /s0/r1/accel/*  │
                  │ /s0/r1/gyro/*   │
                  │ /s0/t1/accel/*  │
                  │ /s0/t1/gyro/*   │
                  │ /s0/mute        │
                  └──────┬──────────┘
                         │
           ┌─────────────┴─────────────┐
           │                           │
    ┌──────▼──────┐             ┌──────▼──────┐
    │  VCV Rack   │             │  Hue Lights │
    │  Port 8011  │             │             │
    │             │             │ Warm (close)│
    │  Layer 1    │             │ Cool (far)  │
    └─────────────┘             └─────────────┘
```

### Implementation Details

**Hysteresis & Debouncing:**
```python
# Prevent flickering at threshold boundary
CLOSE_THRESHOLD = 0.8  # meters
HYSTERESIS = 0.15      # 15cm buffer
DEBOUNCE = 0.5         # 500ms delay

# State zones:
# CLOSE: distance < 0.65m (0.8 - 0.15)
# DEAD ZONE: 0.65m - 0.95m (no state change)
# FAR: distance > 0.95m (0.8 + 0.15)
```

**OSC Routing:**
```python
# Scene 0 uses dedicated port 8011 with /s0/* prefix
scene0_vcv_client.send_message("/s0/r1/accel/x", value)
scene0_vcv_client.send_message("/s0/t1/gyro/z", value)
scene0_vcv_client.send_message("/s0/mute", 1)  # 1=active, 0=inactive
```

### Challenges Encountered

#### Challenge 1: Threshold Flickering
**Problem:** At exactly 0.80m, proximity rapidly toggled between close/far, causing strobing lights.

**Visual Debug Output:**
```
[0.79m] CLOSE → Warm
[0.81m] FAR → Cool
[0.80m] CLOSE → Warm  ← Rapid toggling!
[0.80m] FAR → Cool
[0.79m] CLOSE → Warm
```

**Solution:** Hysteresis implementation
```python
class Scene0State:
    def __init__(self):
        self.r1_is_close = None
        self.r1_last_change_time = 0
    
    def update_proximity(self, distance):
        if self.r1_is_close:
            # Currently close - need distance > threshold + hysteresis
            if distance > (CLOSE_THRESHOLD + HYSTERESIS):
                self.r1_is_close = False
        else:
            # Currently far - need distance < threshold - hysteresis
            if distance < (CLOSE_THRESHOLD - HYSTERESIS):
                self.r1_is_close = True
```

**Result:** ✅ Stable state transitions with 15cm dead zone

#### Challenge 2: White Rocker Interference
**Problem:** R2 (White) was inadvertently sending sensor data even though Scene 0 doesn't use it.

**Solution:** Scene-aware OSC forwarding
```python
def r2_accel_x_handler(unused_addr, x):
    receiver2.accel_x = x
    with scene_lock:
        scene = current_scene
    
    # Scene 0: R2 not used
    if scene == 0:
        return  # Don't forward
    
    # Scene 1, 2: Forward normally
    if scene == 1:
        vcv_client.send_message("/r2/accel/x", x)
```

**Result:** ✅ Clean Scene 0 operation with only R1 + Transmitter data

### Success Metrics
- ✅ Zero flickering with hysteresis
- ✅ Smooth light temperature transitions
- ✅ Isolated R1 control
- ✅ Dedicated OSC namespace (/s0/*)

---

## Phase 3: Scene 1 - Distance-Based Multi-State

### Objective
Create a scene where the **distance between rockers** creates four distinct room states with unique light colors.

### Design Goals
1. Four states based on R1 and R2 proximity to Transmitter
2. Both close → Warm white
3. Both far → Red
4. R1 far, R2 close → Blue
5. R1 close, R2 far → Cool white
6. All sensor data always forwarded to VCV Rack

### Architecture Diagram - Scene 1

```
┌─────────────────────────────────────────────────────────────────┐
│                          SCENE 1                                │
│                 Distance-Based Multi-State                      │
└─────────────────────────────────────────────────────────────────┘

                    ┌──────────────────┐
                    │  Transmitter     │
                    │  (Purple)        │
                    │  BLE Beacon      │
                    └────────┬─────────┘
                             │ RSSI
              ┌──────────────┴──────────────┐
              │                             │
    ┌─────────▼────────┐          ┌────────▼─────────┐
    │  R1 (Copper)     │          │  R2 (White)      │
    │                  │          │                  │
    │  Distance: d1    │          │  Distance: d2    │
    │  Sensors         │          │  Sensors         │
    └─────────┬────────┘          └────────┬─────────┘
              │                             │
              │ OSC 8001, 8004              │ OSC 8002, 8006
              └──────────────┬──────────────┘
                             │
                  ┌──────────▼──────────┐
                  │ Scene 1 Python      │
                  │                     │
                  │ State Logic:        │
                  │ • both_close        │
                  │ • both_far          │
                  │ • r1_far_r2_close   │
                  │ • r1_close_r2_far   │
                  │                     │
                  │ Port 8010 (VCV)     │
                  │ /r1/*, /r2/*        │
                  └──────────┬──────────┘
                             │
               ┌─────────────┴─────────────┐
               │                           │
        ┌──────▼──────┐             ┌──────▼──────┐
        │  VCV Rack   │             │  Hue Lights │
        │  Port 8010  │             │             │
        │             │             │ 4 States:   │
        │  All data   │             │ • Warm (cc) │
        │  from both  │             │ • Red (ff)  │
        │  rockers    │             │ • Blue (fc) │
        └─────────────┘             │ • Cool (cf) │
                                    └─────────────┘
```

### State Machine Logic

```python
# Four-state system with hysteresis
def scene1_check_distance_triggers():
    # Priority order prevents state conflicts
    
    # 1. Both close (highest priority)
    if receiver1.is_close and receiver2.is_close:
        trigger_state("both_close")
        hue_command("warm_white", "t500")
    
    # 2. Both far
    elif not receiver1.is_close and not receiver2.is_close:
        trigger_state("both_far")
        hue_command("red")
    
    # 3. R1 far, R2 close
    elif not receiver1.is_close and receiver2.is_close:
        trigger_state("r1_far_r2_close")
        hue_command("blue")
    
    # 4. R1 close, R2 far
    elif receiver1.is_close and not receiver2.is_close:
        trigger_state("r1_close_r2_far")
        hue_command("cool_white", "t153")
```

### Challenges Encountered

#### Challenge 1: Threshold Overlap Issues
**Problem:** Initially set FAR_THRESHOLD = 2.0m, CLOSE_THRESHOLD = 0.8m. This created three states (close, medium, far) but the "both far" condition never triggered.

**Debug Output:**
```
R1: 1.2m [MEDIUM] | R2: 1.5m [MEDIUM]
State: ??? (no match)
Expected: both_far
Actual: No light change
```

**Root Cause:** With hysteresis, the "far" state required distance >= 2.15m (2.0 + 0.15), which was beyond practical testing range.

**Solution:** Set FAR_THRESHOLD = CLOSE_THRESHOLD = 0.8m, use negation logic
```python
# Instead of: receiver1.is_far and receiver2.is_far
# Use: not receiver1.is_close and not receiver2.is_close
```

**Result:** ✅ All four states reliably detected at practical distances

#### Challenge 2: Hysteresis State Tracking
**Problem:** Each rocker needed three states (close/medium/far) with state-dependent thresholds.

**Solution:** State-aware hysteresis
```python
def update_proximity_scene1(self, distance):
    if self.is_close:
        # Exit close state only if distance > threshold + hysteresis
        if distance > (CLOSE_THRESHOLD + HYSTERESIS):
            self.is_close = False
            self.is_medium = True
    
    elif self.is_far:
        # Exit far state only if distance < threshold - hysteresis
        if distance < (FAR_THRESHOLD - HYSTERESIS):
            self.is_far = False
            self.is_medium = True
    
    else:  # is_medium
        # Check both boundaries
        if distance < (CLOSE_THRESHOLD - HYSTERESIS):
            self.is_close = True
            self.is_medium = False
        elif distance > (FAR_THRESHOLD + HYSTERESIS):
            self.is_far = True
            self.is_medium = False
```

**Result:** ✅ Smooth state transitions without flickering

#### Challenge 3: State Conflict Resolution
**Problem:** When distances changed rapidly, multiple state conditions could briefly be true simultaneously.

**Solution:** Priority-based evaluation with 1.5s cooldown
```python
last_trigger_time = 0
TRIGGER_COOLDOWN = 1.5

def scene1_check_distance_triggers():
    current_time = time.time()
    if current_time - last_trigger_time < TRIGGER_COOLDOWN:
        return  # Ignore rapid changes
    
    # Evaluate in priority order (shown above)
    # First match wins
```

**Result:** ✅ Stable state transitions, no light flickering

### Success Metrics
- ✅ Four distinct states reliably detected
- ✅ No state conflicts or flickering
- ✅ Smooth light transitions
- ✅ All sensor data forwarded to VCV Rack

---

## Phase 4: Scene 2 - Isolation Mode

### Objective
Create a scene where individual rockers can "isolate" by moving far from the Transmitter, triggering unique per-rocker responses.

### Design Goals
1. Each rocker independently isolates at >0.8m
2. Isolation triggers random bulb + random color assignment
3. Only isolated rocker's data sent to VCV Rack
4. Smart bulb assignment (no conflicts between rockers)
5. Return (<0.8m) resets bulb to warm white

### Architecture Diagram - Scene 2

```
┌─────────────────────────────────────────────────────────────────┐
│                          SCENE 2                                │
│                      Isolation Mode                             │
└─────────────────────────────────────────────────────────────────┘

                    ┌──────────────────┐
                    │  Transmitter     │
                    │  (Purple)        │
                    │  BLE Beacon      │
                    └────────┬─────────┘
                             │
              ┌──────────────┴──────────────┐
              │                             │
    ┌─────────▼────────┐          ┌────────▼─────────┐
    │  R1 (Copper)     │          │  R2 (White)      │
    │                  │          │                  │
    │  Isolated?       │          │  Isolated?       │
    │  >0.8m + 0.15    │          │  >0.8m + 0.15    │
    └─────────┬────────┘          └────────┬─────────┘
              │                             │
              └──────────────┬──────────────┘
                             │
                  ┌──────────▼──────────┐
                  │ Scene 2 Python      │
                  │                     │
                  │ Isolation Logic:    │
                  │ • R1 isolated?      │
                  │   → Assign bulb     │
                  │   → Random color    │
                  │   → Send /s2/r1/mute=1
                  │                     │
                  │ • R2 isolated?      │
                  │   → Assign bulb     │
                  │   → Random color    │
                  │   → Send /s2/r2/mute=1
                  │                     │
                  │ Port 8010 (VCV)     │
                  │ /r1/* (if isolated) │
                  │ /r2/* (if isolated) │
                  │ /s2/r1/mute         │
                  │ /s2/r2/mute         │
                  └──────────┬──────────┘
                             │
               ┌─────────────┴─────────────┐
               │                           │
        ┌──────▼──────┐             ┌──────▼──────┐
        │  VCV Rack   │             │  Hue Lights │
        │  Port 8010  │             │  4 Bulbs    │
        │             │             │             │
        │  Isolated   │             │ Smart       │
        │  data only  │             │ Assignment  │
        └─────────────┘             └─────────────┘
```

### Smart Bulb Assignment

```python
# 4 available bulbs
HUE_LIGHTS = [
    {"id": "...", "name": "Lamp 1"},
    {"id": "...", "name": "Lamp 2"},
    {"id": "...", "name": "Light 3"},
    {"id": "...", "name": "Hue Essential lamp 2"}
]

def scene2_trigger_random_bulb(rocker_name):
    rocker = get_rocker(rocker_name)
    
    # Get available bulbs (not assigned to other rocker)
    available_bulbs = [
        bulb for bulb in HUE_LIGHTS 
        if bulb != other_rocker.assigned_bulb
    ]
    
    # Random selection
    random_bulb = random.choice(available_bulbs)
    random_color = random.choice(RANDOM_COLORS)  # 140+ colors
    
    # Assign to rocker
    rocker.assigned_bulb = random_bulb
    rocker.assigned_color = random_color
    
    # Send mute control
    vcv_client.send_message(f"/s2/{rocker_id}/mute", 1)
    
    # Set light
    openhue set light {bulb_id} --color {color}
```

### Isolation State Machine

```
┌─────────────┐
│   NORMAL    │  Both rockers < 0.8m
│  (No data)  │  No lights triggered
└──────┬──────┘
       │
       │ R1 moves >0.95m (0.8 + 0.15 hysteresis)
       ↓
┌─────────────┐
│ R1 ISOLATED │  • Random bulb assigned
│             │  • Random color set
│             │  • /s2/r1/mute = 1
│             │  • R1 data → VCV Rack
└──────┬──────┘
       │
       │ R2 also moves >0.95m
       ↓
┌─────────────┐
│    BOTH     │  • Each has different bulb
│  ISOLATED   │  • Each has random color
│             │  • /s2/r1/mute = 1
│             │  • /s2/r2/mute = 1
│             │  • Both data → VCV Rack
└──────┬──────┘
       │
       │ R1 returns <0.65m (0.8 - 0.15 hysteresis)
       ↓
┌─────────────┐
│ R2 ISOLATED │  • R1 bulb → warm white
│   (only)    │  • R1 assignment cleared
│             │  • /s2/r1/mute = 0
│             │  • Only R2 data → VCV Rack
└─────────────┘
```

### Challenges Encountered

#### Challenge 1: Bulb Assignment Conflicts
**Problem:** When both rockers isolated, they sometimes selected the same bulb.

**Debug Output:**
```
R1 isolates → Lamp 1 → crimson
R2 isolates → Lamp 1 → blue  ← CONFLICT!
Result: Lamp 1 rapidly changes colors
```

**Solution:** Exclusion logic
```python
available_bulbs = [
    bulb for bulb in HUE_LIGHTS 
    if bulb != receiver1.assigned_bulb and 
       bulb != receiver2.assigned_bulb
]
```

**Result:** ✅ Each rocker gets unique bulb

#### Challenge 2: Rapid Isolation/Return Cycling
**Problem:** Without debouncing, rockers at threshold boundary rapidly triggered isolation/return.

**Solution:** Multi-layer debouncing
```python
ISOLATION_THRESHOLD = 0.8
HYSTERESIS = 0.15  # 0.65m - 0.95m dead zone
STATE_CHANGE_DEBOUNCE = 0.8  # 800ms delay
TRIGGER_COOLDOWN = 1.5  # 1.5s between triggers

def update_proximity_scene2(self, distance):
    was_isolated = self.is_isolated
    
    # Hysteresis logic
    if not self.is_isolated and distance > (ISOLATION_THRESHOLD + HYSTERESIS):
        state_changed = True
        self.is_isolated = True
    elif self.is_isolated and distance < (ISOLATION_THRESHOLD - HYSTERESIS):
        state_changed = True
        self.is_isolated = False
    
    # Debounce
    if state_changed:
        if time.time() - self.last_state_change_time < STATE_CHANGE_DEBOUNCE:
            self.is_isolated = was_isolated  # Revert
            return False
        self.last_state_change_time = time.time()
        return True
```

**Result:** ✅ Stable isolation detection, no rapid cycling

#### Challenge 3: OSC Mute Control
**Problem:** VCV Rack needed to know which rocker was isolated to route audio correctly.

**Solution:** Per-rocker mute messages
```python
# When R1 isolates
vcv_client.send_message("/s2/r1/mute", 1)  # Active

# When R1 returns
vcv_client.send_message("/s2/r1/mute", 0)  # Inactive

# VCV Rack uses these as gate signals for VCAs
```

**Result:** ✅ Clean audio routing based on isolation state

### Success Metrics
- ✅ Reliable isolation detection
- ✅ No bulb assignment conflicts
- ✅ 140+ color variations
- ✅ Stable state transitions
- ✅ Per-rocker mute control

---

## Phase 5: Unified System (PlaytestV1)

### Objective
Combine all three scenes into a single system with instant scene switching via GUI.

### Design Goals
1. One Python program controls all scenes
2. One set of Arduino sketches works for all scenes
3. GUI with three buttons for instant switching
4. No code changes or board reflashing needed
5. Terminal monitor for debugging sensor data

### Architecture Diagram - PlaytestV1

```
┌──────────────────────────────────────────────────────────────────────┐
│                      PLAYTESTV1 UNIFIED SYSTEM                       │
└──────────────────────────────────────────────────────────────────────┘

┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│ Transmitter_    │    │ Receiver1_      │    │ Receiver2_      │
│ Purple.ino      │    │ Copper.ino      │    │ White.ino       │
│                 │    │                 │    │                 │
│ Universal       │    │ Universal       │    │ Universal       │
│ Works for       │    │ Works for       │    │ Works for       │
│ ALL scenes      │    │ ALL scenes      │    │ ALL scenes      │
└────────┬────────┘    └────────┬────────┘    └────────┬────────┘
         │                      │                       │
         │ OSC 8005             │ OSC 8001, 8004        │ OSC 8002, 8006
         └──────────────────────┴───────────────────────┘
                                │
                    ┌───────────▼───────────┐
                    │ wobble_unified_       │
                    │ processor.py          │
                    │                       │
                    │ ┌───────────────────┐ │
                    │ │   Tkinter GUI     │ │
                    │ │ ┌───┐ ┌───┐ ┌───┐ │ │
                    │ │ │ 0 │ │ 1 │ │ 2 │ │ │
                    │ │ └───┘ └───┘ └───┘ │ │
                    │ │  Scene Buttons    │ │
                    │ └───────────────────┘ │
                    │                       │
                    │ Scene Logic:          │
                    │ • if scene == 0: ...  │
                    │ • if scene == 1: ...  │
                    │ • if scene == 2: ...  │
                    │                       │
                    │ Terminal Monitor:     │
                    │ • Real-time sensor    │
                    │ • Min/Max tracking    │
                    │ • Visual bar charts   │
                    └───────────┬───────────┘
                                │
                ┌───────────────┴───────────────┐
                │                               │
         ┌──────▼──────┐                 ┌──────▼──────┐
         │  VCV Rack   │                 │  Hue Lights │
         │             │                 │             │
         │ Port 8010   │                 │  OpenHue    │
         │ Port 8011   │                 │  CLI        │
         └─────────────┘                 └─────────────┘
```

### GUI Implementation

```python
def create_gui():
    root = tk.Tk()
    root.title("Wobble Unified Processor")
    
    # Scene 0 button (Yellow)
    scene0_btn = tk.Button(
        text="Scene 0\nIndividual Layers",
        command=lambda: switch_to_scene(0),
        bg="#FFD700"
    )
    
    # Scene 1 button (Blue)
    scene1_btn = tk.Button(
        text="Scene 1\nDistance States",
        command=lambda: switch_to_scene(1),
        bg="#87CEEB"
    )
    
    # Scene 2 button (Green)
    scene2_btn = tk.Button(
        text="Scene 2\nIsolation Mode",
        command=lambda: switch_to_scene(2),
        bg="#98FB98"
    )
    
    return root
```

### Scene Switching Logic

```python
def switch_to_scene(scene_num):
    global current_scene
    
    with scene_lock:
        print(f"SWITCHING TO SCENE {scene_num}")
        current_scene = scene_num
        
        # Scene-specific mute controls
        if scene_num == 0:
            scene0_vcv_client.send_message("/s0/mute", 1)  # Active
        else:
            scene0_vcv_client.send_message("/s0/mute", 0)  # Inactive
        
        if scene_num == 2:
            # Initialize Scene 2 mute states
            vcv_client.send_message("/s2/r1/mute", 1 if receiver1.is_isolated else 0)
            vcv_client.send_message("/s2/r2/mute", 1 if receiver2.is_isolated else 0)
        else:
            # Reset Scene 2 mutes
            vcv_client.send_message("/s2/r1/mute", 0)
            vcv_client.send_message("/s2/r2/mute", 0)
        
        # Reset scene-specific states
        reset_scene_state(scene_num)
```

### Terminal Movement Monitor

```
════════════════════════════════════════════════════════════════════
WOBBLE MOVEMENT MONITOR - Real-time Sensor Data with Min/Max Tracking
════════════════════════════════════════════════════════════════════
Press Ctrl+C in terminal to reset min/max values

┌─── RECEIVER 1 (COPPER) ─────────────────────────────────────────┐
│ ACCELEROMETER (m/s²)
│  X:   -2.45 [  -5.23 to    3.67]  ████████████████░░░░░░░░░░░░
│  Y:    0.12 [  -4.89 to    4.12]  ████████████████████████░░░░
│  Z:    9.81 [   8.45 to   11.23]  ████████████████████████████░░
│
│ GYROSCOPE (rad/s)
│  X:    0.03 [  -1.23 to    1.45]  ██████████████████████░░░░░░
│  Y:   -0.15 [  -2.01 to    1.89]  ████████████████████░░░░░░░░
│  Z:    0.00 [  -0.98 to    1.12]  ████████████████████░░░░░░░░
└──────────────────────────────────────────────────────────────────┘

┌─── RECEIVER 2 (WHITE) ──────────────────────────────────────────┐
│ ACCELEROMETER (m/s²)
│  X:    1.23 [  -3.45 to    5.67]  ████████████████████████░░░░
│  Y:   -0.56 [  -6.78 to    2.34]  ██████████████████░░░░░░░░░░
│  Z:   10.12 [   7.89 to   12.45]  ███████████████████████████░░
│
│ GYROSCOPE (rad/s)
│  X:    0.45 [  -1.56 to    2.34]  ████████████████████████░░░░
│  Y:   -0.23 [  -1.78 to    1.23]  ██████████████████░░░░░░░░░░
│  Z:    0.12 [  -0.89 to    1.45]  ██████████████████████░░░░░░
└──────────────────────────────────────────────────────────────────┘

Current Scene: 1 | Distance R1: 1.23m | Distance R2: 0.75m
```

### Unified Arduino Architecture

**Key Design Decision:** All Arduino sketches are scene-agnostic. They simply:
1. Read sensors at 104Hz
2. Broadcast/scan BLE
3. Calculate RSSI distance
4. Send OSC messages

**No scene logic in Arduino code.** All scene behavior is in Python.

```cpp
// Universal Arduino pattern
void loop() {
    // Read sensor
    sensors_event_t accel, gyro, temp;
    sox.getEvent(&accel, &gyro, &temp);
    
    // Send OSC (always)
    sendSensorBundle(accel, gyro);
    
    // Calculate distance (receivers only)
    if (bleDeviceFound) {
        float distance = rssiToDistance(smoothedRSSI);
        sendProximityOSC(distance);
    }
    
    // Python processor handles scene logic
}
```

### Challenges Encountered

#### Challenge 1: Thread-Safe Scene Switching
**Problem:** GUI button clicks on main thread, OSC handlers on separate threads → race conditions.

**Solution:** Threading locks
```python
scene_lock = threading.Lock()

def switch_to_scene(scene_num):
    with scene_lock:
        current_scene = scene_num
        # ... scene switching logic

def r1_accel_x_handler(unused_addr, x):
    with scene_lock:
        scene = current_scene
    
    if scene == 0:
        # Scene 0 logic
```

**Result:** ✅ No race conditions, stable scene switching

#### Challenge 2: State Persistence Across Scenes
**Problem:** Switching from Scene 2 back to Scene 0, old bulb assignments persisted.

**Solution:** State reset on scene switch
```python
def switch_to_scene(scene_num):
    # Reset scene-specific states
    if scene_num == 0:
        scene0_state = Scene0State()
    elif scene_num == 1:
        last_state_scene1 = None
    elif scene_num == 2:
        # Reset any active bulb assignments
        if receiver1.assigned_bulb:
            scene2_reset_bulb("R1 (Copper)")
        if receiver2.assigned_bulb:
            scene2_reset_bulb("R2 (White)")
```

**Result:** ✅ Clean state on every scene switch

#### Challenge 3: Multiple OSC Ports
**Problem:** Scene 0 needs dedicated port (8011), Scenes 1 & 2 share port (8010).

**Solution:** Multiple UDP clients
```python
vcv_client = SimpleUDPClient("192.168.50.201", 8010)  # Scene 1, 2
scene0_vcv_client = SimpleUDPClient("192.168.50.201", 8011)  # Scene 0

# Scene-aware sending
if scene == 0:
    scene0_vcv_client.send_message("/s0/r1/accel/x", x)
else:
    vcv_client.send_message("/r1/accel/x", x)
```

**Result:** ✅ Proper OSC routing per scene

### Success Metrics
- ✅ Instant scene switching (<100ms)
- ✅ No Arduino reflashing needed
- ✅ Visual feedback in GUI and terminal
- ✅ All three scenes fully functional
- ✅ Zero state conflicts

---

## Technical Challenges & Solutions

### Challenge Matrix

| Challenge | Phase | Root Cause | Solution | Result |
|-----------|-------|------------|----------|--------|
| RSSI Instability | 1 | Radio interference | Rolling average (5 samples) | ✅ Stable distance |
| WiFi-BLE Conflict | 1 | Shared radio hardware | Dual-core separation | ✅ No drops |
| Data Rate Overload | 1 | 104Hz sensor + network | Throttle to 25Hz OSC | ✅ Responsive |
| Threshold Flickering | 2 | Exact boundary crossing | Hysteresis (0.15m) | ✅ No flicker |
| State Overlap | 3 | Multiple conditions true | Priority evaluation | ✅ Clean states |
| FAR not detecting | 3 | Threshold too far (2.0m) | Use 0.8m + negation | ✅ All states work |
| Bulb Conflicts | 4 | Random selection collision | Exclusion logic | ✅ Unique bulbs |
| Rapid Cycling | 4 | No debouncing | Multi-layer debounce | ✅ Stable isolation |
| Scene Race Conditions | 5 | Multi-threaded access | Threading locks | ✅ Thread-safe |
| State Persistence | 5 | No cleanup on switch | State reset logic | ✅ Clean switches |

---

## Debug Tools & Monitoring

### 1. Arduino Serial Monitor

**Purpose:** Real-time firmware debugging

**Output Example:**
```
Wobble Unified - Receiver1 (Copper)
QT Py ESP32-S3
========================================

✓ WiFi connected!
  IP Address: 192.168.50.100
  OSC Local Port: 9001
  OSC Destination: 192.168.50.201:8001 → Python

✓ LSM6DSOX Found!
  Accel Range: ±4G
  Gyro Range: ±500 DPS
  Sample Rate: 104 Hz

✓ BLE Scanner started!
  Scanning for: QTPy_ESP32
  Service UUID: 4fafc201-1fb5-459e-8fcc-c5c9c331914b

========================================
System ready!
========================================

[BLE] Found: QTPy_ESP32 | RSSI: -65 dBm
[Smooth] RSSI Buffer: [-67, -63, -65, -68, -62]
[Smooth] Average: -65 dBm
[Distance] 0.35m | State: CLOSE
📡 Proximity sent: 0.35m, in_range=1

[Sensor] Accel: (1.23, -0.45, 9.81) | Gyro: (0.01, -0.02, 0.00)
📡 Sensor bundle sent

[BLE] Lost signal | RSSI: -95 dBm
[Distance] 2.15m | State: FAR
📡 Proximity sent: 2.15m, in_range=0
```

### 2. Python Terminal Monitor

**Purpose:** Real-time sensor visualization with min/max tracking

**Features:**
- Visual bar charts using █ (filled) and ░ (empty)
- Automatic min/max tracking
- 10Hz refresh rate
- Ctrl+C to reset tracking

**Implementation:**
```python
def create_bar(value, min_val, max_val, width=40):
    if max_val == min_val:
        normalized = 0.5
    else:
        normalized = (value - min_val) / (max_val - min_val)
    
    bar_length = int(normalized * width)
    bar = "█" * bar_length + "░" * (width - bar_length)
    return bar

def display_movement_monitor():
    while movement_monitor.display_enabled:
        os.system('clear')
        
        # Display each rocker's data with bars
        print("RECEIVER 1 (COPPER)")
        print(f"  X: {r1.accel_x:7.2f} [{min:7.2f} to {max:7.2f}]  {bar}")
        # ... repeat for all axes
        
        time.sleep(0.1)  # 10Hz
```

### 3. Python Console Output

**Purpose:** Event logging and state changes

**Output Example:**
```
====================================================================
Wobble Unified Processor
====================================================================

Configuration:
  Close Threshold: ≤0.8m
  Far Threshold: ≥0.8m
  Isolation Threshold: 0.8m ±0.15m
  VCV Rack Output: port 8010

Starting OSC input servers:
✓ R1 Proximity server listening on port 8001
✓ R2 Proximity server listening on port 8002
✓ R1 Sensors server listening on port 8004
✓ R2 Sensors server listening on port 8006
✓ Transmitter server listening on port 8005

OSC output to VCV Rack:
  Scene 0: port 8011 (addresses: /s0/r1/*, /s0/t1/*, /s0/mute)
  Scene 1, 2: port 8010
====================================================================

Initializing Scene 0 as active...
  Scene 0 active: ON (1)

Starting terminal movement monitor...
Starting GUI...

============================================================
SWITCHING TO SCENE 1
============================================================
  Scene 0 active: OFF (0)
  Scene 1 state reset

🔵 SCENE 1: BOTH CLOSE - Warm white (t500)
  R1 (Copper): 0.45m
  R2 (White): 0.62m
   ✓ Room → Warm white

🔴 SCENE 1: BOTH FAR - Red
  R1 (Copper): 1.23m
  R2 (White): 1.45m
   ✓ Room → Red

============================================================
SWITCHING TO SCENE 2
============================================================
  Scene 0 active: OFF (0)
  Scene 2 R1 mute initialized: 0
  Scene 2 R2 mute initialized: 0
  Scene 2 state reset

💡 SCENE 2: R1 (Copper) ISOLATED - Lamp 1 → crimson
   ✓ Lamp 1 → crimson

🔄 SCENE 2: R1 (Copper) RETURNED - Lamp 1 → Warm white (t500)
   ✓ Lamp 1 → Warm white
```

### 4. OSC Monitor (test_osc_monitor.py)

**Purpose:** Verify OSC message transmission

**Usage:**
```bash
python3 test_osc_monitor.py
```

**Output:**
```
OSC Monitor - Listening on all ports
====================================

[Port 8001] /proximity/distance: 0.45, 1
[Port 8004] /accel/x: 1.23
[Port 8004] /accel/y: -0.45
[Port 8004] /accel/z: 9.81
[Port 8004] /gyro/x: 0.01
[Port 8004] /gyro/y: -0.02
[Port 8004] /gyro/z: 0.00
[Port 8005] /accel/x: -0.34
[Port 8005] /accel/y: 0.67
...
```

### 5. VCV Rack OSC-CV Module

**Purpose:** Visual feedback of OSC messages in audio environment

**Configuration:**
```
Module: OSC-CV (or similar)
Port: 8010 (Scene 1, 2) or 8011 (Scene 0)

Mappings:
/s0/r1/accel/x → CV Out 1 (visual display)
/s0/r1/gyro/z → CV Out 2
/s0/mute → CV Out 3 (gate visualization)
```

**Visual Feedback:**
- LEDs light up when OSC messages received
- Voltage displays show current sensor values
- Scope displays show waveforms

---

## Lessons Learned

### 1. Hardware Design

**✅ What Worked:**
- ESP32-S3's dual-core architecture perfect for BLE + WiFi
- LSM6DSOX provided reliable, high-frequency motion data
- BLE RSSI proved sufficient for proximity detection
- Small form factor enabled embedded "rocker" design

**❌ What Didn't Work:**
- Initial attempt to use WiFi RSSI for distance (too unreliable)
- Single-core task scheduling caused connection drops
- 104Hz OSC transmission saturated network

**📚 Lesson:** Separate concerns on hardware - use dual cores, throttle data rates, choose right communication protocol for each task.

### 2. Proximity Detection

**✅ What Worked:**
- Rolling average smoothing (5 samples)
- Hysteresis zones (15cm buffer)
- Debouncing (500ms-1500ms depending on scene)
- RSSI-to-distance exponential formula

**❌ What Didn't Work:**
- Raw RSSI values (too noisy)
- Single threshold (caused flickering)
- 2.0m far threshold (impractical range)

**📚 Lesson:** Signal processing is essential - smooth, debounce, add hysteresis. Real-world testing reveals practical limitations.

### 3. State Machine Design

**✅ What Worked:**
- Priority-based state evaluation
- State-dependent hysteresis thresholds
- Per-scene state objects
- Thread-safe state access

**❌ What Didn't Work:**
- Simple threshold comparisons (unstable)
- Global state without locking (race conditions)
- No state reset on scene switch (persistence bugs)

**📚 Lesson:** State machines need careful design - consider transitions, conflicts, thread safety, and cleanup.

### 4. Software Architecture

**✅ What Worked:**
- Scene-agnostic Arduino firmware
- Python middleware for logic
- Separate OSC namespaces per scene (/s0/*, /s2/*)
- Multi-threaded OSC servers

**❌ What Didn't Work:**
- Initial monolithic Python script (hard to debug)
- Scene logic in Arduino (inflexible)
- Single OSC port for all scenes (namespace collision)

**📚 Lesson:** Separation of concerns - firmware handles hardware, middleware handles logic. Clear namespacing prevents conflicts.

### 5. Debug Tooling

**✅ What Worked:**
- Real-time terminal monitor with bar charts
- Arduino Serial Monitor with detailed logging
- Console event logging with emojis
- OSC monitor for message verification

**❌ What Didn't Work:**
- Debugging without visual feedback (slow)
- No min/max tracking (missed edge cases)
- Silent failures in OpenHue CLI (hard to diagnose)

**📚 Lesson:** Invest in debug tools early - visualization accelerates development, logging catches edge cases.

### 6. User Experience

**✅ What Worked:**
- Instant scene switching via GUI
- Visual feedback (lights + terminal)
- Unified system (no code changes needed)
- Clear color coding (yellow/blue/green buttons)

**❌ What Didn't Work:**
- Initial CLI-only interface (cumbersome)
- No visual sensor feedback (hard to calibrate)
- Separate programs per scene (workflow friction)

**📚 Lesson:** UX matters even for art installations - GUIs, visual feedback, and unified workflows improve both development and performance.

### 7. Iterative Development

**✅ What Worked:**
- Building scenes incrementally (0 → 1 → 2)
- Validating each phase before moving on
- Keeping reference implementation for comparison
- Unified system as final integration

**❌ What Didn't Work:**
- Trying to build all features at once (overwhelming)
- Changing Arduino code for each scene (brittle)
- No version control initially (lost work)

**📚 Lesson:** Iterate, validate, integrate. Each phase builds on previous success.

---

## System Specifications

### Final Configuration

**Hardware:**
- 3x Adafruit QT Py ESP32-S3
- 3x LSM6DSOX 6-axis IMU
- 4x Philips Hue Smart Bulbs
- WiFi Network: Dr.Wifi
- Laptop: 192.168.50.201

**Software:**
- Arduino IDE 2.x
- Python 3.x
- Libraries: pythonosc, tkinter
- OpenHue CLI
- VCV Rack 2.x

**Network Topology:**
```
OSC Input Ports:
  8001 - R1 Proximity Events
  8002 - R2 Proximity Events
  8004 - R1 Sensor Data
  8005 - Transmitter Sensor Data
  8006 - R2 Sensor Data

OSC Output Ports:
  8010 - VCV Rack (Scene 1, 2)
  8011 - VCV Rack (Scene 0)

UDP Protocol: Open Sound Control (OSC)
Update Rate: 25Hz (sensors), 5Hz (proximity)
```

**OSC Address Namespaces:**
```
Scene 0 (Port 8011):
  /s0/r1/accel/x,y,z
  /s0/r1/gyro/x,y,z
  /s0/r1/proximity/distance
  /s0/t1/accel/x,y,z
  /s0/t1/gyro/x,y,z
  /s0/mute (1=active, 0=inactive)

Scene 1 (Port 8010):
  /r1/accel/x,y,z
  /r1/gyro/x,y,z
  /r1/proximity/distance
  /r2/accel/x,y,z
  /r2/gyro/x,y,z
  /r2/proximity/distance

Scene 2 (Port 8010):
  /r1/* (when isolated)
  /r2/* (when isolated)
  /s2/r1/mute (1=isolated, 0=not)
  /s2/r2/mute (1=isolated, 0=not)
```

---

## Future Development

### Potential Enhancements

1. **Additional Scenes**
   - Scene 3: Gestural control (recognize specific movements)
   - Scene 4: Collaborative mode (requires coordinated rocker movements)
   - Scene 5: Environmental response (integrate external sensors)

2. **Hardware Improvements**
   - Add haptic feedback (vibration motors)
   - Battery power (eliminate USB cables)
   - Wireless charging docks
   - Custom PCB integration

3. **Software Features**
   - Scene sequencing / automation
   - Recording and playback of rocker movements
   - MIDI output in addition to OSC
   - Web-based control interface
   - Cloud logging and analytics

4. **Interaction Design**
   - Machine learning for gesture recognition
   - Adaptive thresholds (learns from usage)
   - Multi-rocker choreography templates
   - Audience participation modes

5. **Visual Integration**
   - Projection mapping synchronized with movement
   - LED strips on rockers
   - DMX lighting control
   - Video synthesis (TouchDesigner integration)

### Known Limitations

1. **Range:** BLE proximity limited to ~2-3 meters practical range
2. **Latency:** ~50-100ms total system latency
3. **Interference:** WiFi congestion affects OSC delivery
4. **Calibration:** RSSI-distance relationship varies by environment
5. **Power:** USB tethering limits rocker placement

### Research Directions

1. **Ultra-Wideband (UWB):** More accurate distance measurement
2. **Computer Vision:** Optical tracking for position + orientation
3. **Mesh Networking:** Direct rocker-to-rocker communication
4. **Edge ML:** On-device gesture recognition
5. **Multi-Room:** Scale to multiple spaces with synchronized control

---

## Conclusion

The Wobble project successfully evolved from a two-rocker proximity detector to a sophisticated three-scene interactive system. Through iterative development, careful debugging, and thoughtful architecture, we achieved:

✅ **Reliable Hardware Communication** - Stable BLE + WiFi on ESP32  
✅ **Rich Interaction Modes** - Three distinct scenes with unique behaviors  
✅ **Unified Control** - Single system, instant scene switching  
✅ **Professional Debug Tools** - Real-time monitoring and visualization  
✅ **Scalable Architecture** - Ready for future expansion  

The journey from initial prototype to PlaytestV1 demonstrated the importance of:
- **Iterative development** - Build, test, refine
- **Separation of concerns** - Firmware vs middleware vs output
- **Debug tooling** - Invest early, reap benefits throughout
- **User experience** - Even technical systems benefit from good UX
- **Documentation** - Record challenges and solutions for future reference

This project serves as both a functional interactive installation and a comprehensive case study in embedded systems development, signal processing, and creative technology integration.

---

## Appendix: File Structure

```
Wobble/
├── README.md                          # Project overview
├── DEVELOPMENT_JOURNEY.md             # This document
├── LICENSE
├── InteractionPater.md
│
├── Reference/                         # Phase 1: Initial prototype
│   ├── Transmitter_BLE_LSM6.ino
│   ├── Receiver_BLE_LSM6.ino
│   ├── osc_hue_control.py
│   ├── README.md
│   └── SYSTEM_ARCHITECTURE.md
│
├── Scene 0/                           # Phase 2: Individual layers
│   ├── Transmitter_Scene0.ino
│   ├── Receiver_Scene0.ino
│   ├── osc_scene0_hue_control.py
│   ├── monitor_sensor_ranges.py
│   └── README.md
│
├── Scene1/                            # Phase 3: Multi-state distance
│   ├── Transmitter_Scene1.ino
│   ├── Receiver1_Scene1.ino
│   ├── Receiver2_Scene1.ino
│   ├── osc_scene1_processor.py
│   ├── test_osc_monitor.py
│   └── README.md
│
├── Scene2/                            # Phase 4: Isolation mode
│   ├── Transmitter_Scene2.ino
│   ├── Receiver_Scene2.ino
│   ├── osc_scene2_processor.py
│   └── README.md
│
└── PlaytestV1/                        # Phase 5: Unified system
    ├── Transmitter_Purple.ino         # Universal Arduino sketches
    ├── Receiver1_Copper.ino
    ├── Receiver2_White.ino
    ├── wobble_unified_processor.py    # Unified Python controller
    └── README.md                      # Complete documentation
```

---

*Document Version: 1.0*  
*Last Updated: February 18, 2026*  
*Project: Wobble - Interactive Motion-Controlled Audio-Visual System*  
*Author: Joshua Pothen*
