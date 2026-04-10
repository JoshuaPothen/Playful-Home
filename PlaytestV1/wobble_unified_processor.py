#!/usr/bin/env python3
"""
Wobble Unified Processor - All Scenes in One
Three-rocker system with GUI scene switching:
- Receiver 1 (Copper) proximity + sensors → ports 8001, 8004
- Receiver 2 (White) proximity + sensors → ports 8002, 8006  
- Transmitter (Purple) sensors → port 8005

Scenes:
- Scene 0: Individual layer control (frequency/pitch modulation)
- Scene 1: Distance-based multi-state control (4 room states)
- Scene 2: Individual isolation mode (per-rocker bulb assignment)

Outputs:
- Hue light commands via OpenHue CLI
- Sensor data forwarded to VCV Rack on port 8010
- Real-time terminal monitor with movement data visualization

Terminal Monitor:
- Displays live accelerometer and gyroscope data for all three rockers
- Shows visual bar charts with min/max tracking
- Press Ctrl+C to reset min/max values
- Updates 10 times per second (100ms refresh rate)
"""

import subprocess
import time
import threading
import random
import json
import asyncio
import math
import uuid
import tkinter as tk
from tkinter import ttk
from pythonosc import dispatcher, osc_server
from pythonosc.udp_client import SimpleUDPClient
import os
import sys

# ===== CONFIGURATION =====
R1_PROXIMITY_PORT = 8001     # Receiver1 proximity events
R2_PROXIMITY_PORT = 8002     # Receiver2 proximity events
R1_SENSOR_PORT = 8004        # Receiver1 sensor data
R2_SENSOR_PORT = 8006        # Receiver2 sensor data
TRANSMITTER_PORT = 8005      # Transmitter sensor data
VCV_RACK_PORT = 8010         # Output to VCV Rack (all scenes)

# ===== BACKUP PORT CONFIGURATION =====
R1B_PROXIMITY_PORT  = 8101   # Backup Receiver 1 proximity
R2B_PROXIMITY_PORT  = 8102   # Backup Receiver 2 proximity
R1B_SENSOR_PORT     = 8104   # Backup Receiver 1 sensors
TRANSMITTER_B_PORT  = 8105   # Backup Transmitter sensors
R2B_SENSOR_PORT     = 8106   # Backup Receiver 2 sensors

# Source selection flags (False = primary, True = backup)
r1_use_backup = False
r2_use_backup = False
tx_use_backup = False
backup_source_lock = threading.Lock()

# Distance thresholds (meters, RSSI-based)
CLOSE_THRESHOLD = 0.8
FAR_THRESHOLD = 0.8  # Changed from 2.0 - using same as close threshold
ISOLATION_THRESHOLD = 0.8
HYSTERESIS = 0.15

# ===== PHASE 5 — PUSHER LIVE DASHBOARD =====
# Credentials are loaded from PlaytestV1/.env (gitignored).
# Copy PlaytestV1/.env.example → PlaytestV1/.env and fill in your values.
def _load_env_file():
    """Load KEY=VALUE pairs from .env next to this script into os.environ (no dependencies)."""
    env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
    if not os.path.exists(env_path):
        return
    with open(env_path) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, val = line.partition("=")
            os.environ.setdefault(key.strip(), val.strip())

_load_env_file()

PUSHER_ENABLED      = os.environ.get("PUSHER_APP_ID", "") != ""
PUSHER_APP_ID       = os.environ.get("PUSHER_APP_ID",   "")
PUSHER_KEY          = os.environ.get("PUSHER_KEY",       "")
PUSHER_SECRET       = os.environ.get("PUSHER_SECRET",    "")
PUSHER_CLUSTER      = os.environ.get("PUSHER_CLUSTER",   "ap4")
PUSHER_CHANNEL      = "wobble-database"
PUSHER_BROADCAST_HZ = 5       # state broadcasts per second (keep ≤10 to stay within free tier)
VERCEL_URL          = os.environ.get("VERCEL_URL", "")

# ===== SUPABASE =====
SUPABASE_URL = os.environ.get("SUPABASE_URL", "")
SUPABASE_KEY = os.environ.get("SUPABASE_SERVICE_KEY", "")
_supabase_client = None  # set in main() if credentials present

# ===== PHASE 5b — WEBSOCKET SERVER =====
WS_PORT         = 8765
WS_ENABLED      = True
WS_BROADCAST_HZ = 5

_ws_loop    = None   # asyncio event loop in the WS daemon thread
_ws_clients = set()  # active WebSocket connections

# Config file path
CONFIG_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.json")

def _load_config():
    """Load thresholds from config.json if it exists"""
    global CLOSE_THRESHOLD, FAR_THRESHOLD, HYSTERESIS
    global WOBBLE_ACTIVE_THRESHOLD, WOBBLE_IDLE_THRESHOLD, SESSION_TIMEOUT_S
    if not os.path.exists(CONFIG_PATH):
        return
    try:
        with open(CONFIG_PATH) as f:
            cfg = json.load(f)
        CLOSE_THRESHOLD = float(cfg.get("close_threshold", CLOSE_THRESHOLD))
        FAR_THRESHOLD   = float(cfg.get("far_threshold",   FAR_THRESHOLD))
        HYSTERESIS      = float(cfg.get("hysteresis",      HYSTERESIS))
        WOBBLE_ACTIVE_THRESHOLD = float(cfg.get("wobble_active_threshold", WOBBLE_ACTIVE_THRESHOLD))
        WOBBLE_IDLE_THRESHOLD   = float(cfg.get("wobble_idle_threshold",   WOBBLE_IDLE_THRESHOLD))
        SESSION_TIMEOUT_S       = float(cfg.get("session_timeout_s",       SESSION_TIMEOUT_S))
        print(f"  Loaded config: close={CLOSE_THRESHOLD}m far={FAR_THRESHOLD}m hyst={HYSTERESIS}m")
        print(f"  Activity: active={WOBBLE_ACTIVE_THRESHOLD} idle={WOBBLE_IDLE_THRESHOLD} timeout={SESSION_TIMEOUT_S}s")
    except Exception as e:
        print(f"  Config load error: {e}")

def _save_config():
    """Save current thresholds to config.json"""
    try:
        with open(CONFIG_PATH, "w") as f:
            json.dump({
                "close_threshold": CLOSE_THRESHOLD,
                "far_threshold":   FAR_THRESHOLD,
                "hysteresis":      HYSTERESIS,
                "wobble_active_threshold": WOBBLE_ACTIVE_THRESHOLD,
                "wobble_idle_threshold":   WOBBLE_IDLE_THRESHOLD,
                "session_timeout_s":       SESSION_TIMEOUT_S,
            }, f, indent=2)
        log_event("Settings saved", "scene")
        print(f"  Config saved to {CONFIG_PATH}")
    except Exception as e:
        print(f"  Config save error: {e}")

# Debounce timing (seconds)
TRIGGER_COOLDOWN = 1.5
STATE_CHANGE_DEBOUNCE = 0.8

# OpenHue room ID
HUE_ROOM_ID = "81413d75-a3d6-4695-b54e-6e1e4adeb93f"

# Hue Light IDs
HUE_LIGHTS = [
    {"id": "696ad9e0-cd79-46e4-96e7-3868a4b754ee", "name": "Hue Essential lamp 3"},  # tall lamp
    {"id": "efbee8b3-343a-4d98-b891-52b75e060faf", "name": "Strip"},                  # under table strip
    {"id": "60f83ec4-f4e7-4151-bcb2-6480854d3153", "name": "Lamp 2"},                 # office table
    {"id": "bb5eb832-a16a-4936-8ef4-6379e093a485", "name": "Hue Essential lamp 2"}   # side table
]

# Random colors for Scene 2
RANDOM_COLORS = [
    "alice_blue", "antique_white", "aqua", "aqua_marine", "azure", "beige", "bisque",
    "blanched_almond", "blue", "blue_violet", "brown", "burly_wood", "cadet_blue",
    "chartreuse", "chocolate", "coral", "corn_flower_blue", "corn_silk", "crimson",
    "cyan", "dark_blue", "dark_cyan", "dark_golden_rod", "dark_gray", "dark_green",
    "dark_khaki", "dark_magenta", "dark_olive_green", "dark_orange", "dark_orchid",
    "dark_red", "dark_salmon", "dark_sea_green", "dark_slate_blue", "dark_slate_gray",
    "dark_turquoise", "dark_violet", "deep_pink", "deep_sky_blue", "dim_gray",
    "dodger_blue", "firebrick", "floral_white", "forest_green", "fuchsia", "gainsboro",
    "ghost_white", "gold", "golden_rod", "gray", "green", "green_yellow", "honeydew",
    "hot_pink", "indian_red", "indigo", "ivory", "khaki", "lavender", "lavender_blush",
    "lawn_green", "lemon_chiffon", "light_blue", "light_coral", "light_cyan",
    "light_gray", "light_green", "light_pink", "light_salmon", "light_sea_green",
    "light_sky_blue", "light_slate_gray", "light_steel_blue", "light_yellow", "lime",
    "lime_green", "linen", "magenta", "maroon", "medium_aqua_marine", "medium_blue",
    "medium_orchid", "medium_purple", "medium_sea_green", "medium_slate_blue",
    "medium_spring_green", "medium_turquoise", "medium_violet_red", "midnight_blue",
    "mint_cream", "misty_rose", "moccasin", "navajo_white", "navy", "old_lace",
    "olive", "olive_drab", "orange", "orange_red", "orchid", "pale_golden_rod",
    "pale_green", "pale_turquoise", "pale_violet_red", "papaya_whip", "peach_puff",
    "peru", "pink", "plum", "powder_blue", "purple", "red", "rosy_brown", "royal_blue",
    "saddle_brown", "salmon", "sandy_brown", "sea_green", "sea_shell", "sienna",
    "silver", "sky_blue", "slate_blue", "slate_gray", "snow", "spring_green",
    "steel_blue", "tan", "teal", "thistle", "tomato", "turquoise", "violet", "wheat",
    "white", "white_smoke", "yellow", "yellow_green"
]

# ===== GLOBAL STATE =====
class MovementMonitor:
    """Track min/max values for movement data visualization"""
    def __init__(self):
        self.lock = threading.Lock()
        # R1 (Copper)
        self.r1_accel_x_min = 0.0
        self.r1_accel_x_max = 0.0
        self.r1_accel_y_min = 0.0
        self.r1_accel_y_max = 0.0
        self.r1_accel_z_min = 0.0
        self.r1_accel_z_max = 0.0
        self.r1_gyro_x_min = 0.0
        self.r1_gyro_x_max = 0.0
        self.r1_gyro_y_min = 0.0
        self.r1_gyro_y_max = 0.0
        self.r1_gyro_z_min = 0.0
        self.r1_gyro_z_max = 0.0
        
        # R2 (White)
        self.r2_accel_x_min = 0.0
        self.r2_accel_x_max = 0.0
        self.r2_accel_y_min = 0.0
        self.r2_accel_y_max = 0.0
        self.r2_accel_z_min = 0.0
        self.r2_accel_z_max = 0.0
        self.r2_gyro_x_min = 0.0
        self.r2_gyro_x_max = 0.0
        self.r2_gyro_y_min = 0.0
        self.r2_gyro_y_max = 0.0
        self.r2_gyro_z_min = 0.0
        self.r2_gyro_z_max = 0.0
        
        # Transmitter (Purple)
        self.tx_accel_x_min = 0.0
        self.tx_accel_x_max = 0.0
        self.tx_accel_y_min = 0.0
        self.tx_accel_y_max = 0.0
        self.tx_accel_z_min = 0.0
        self.tx_accel_z_max = 0.0
        self.tx_gyro_x_min = 0.0
        self.tx_gyro_x_max = 0.0
        self.tx_gyro_y_min = 0.0
        self.tx_gyro_y_max = 0.0
        self.tx_gyro_z_min = 0.0
        self.tx_gyro_z_max = 0.0
        
        self.display_enabled = True
    
    def update_r1(self, accel_x, accel_y, accel_z, gyro_x, gyro_y, gyro_z):
        with self.lock:
            self.r1_accel_x_min = min(self.r1_accel_x_min, accel_x)
            self.r1_accel_x_max = max(self.r1_accel_x_max, accel_x)
            self.r1_accel_y_min = min(self.r1_accel_y_min, accel_y)
            self.r1_accel_y_max = max(self.r1_accel_y_max, accel_y)
            self.r1_accel_z_min = min(self.r1_accel_z_min, accel_z)
            self.r1_accel_z_max = max(self.r1_accel_z_max, accel_z)
            self.r1_gyro_x_min = min(self.r1_gyro_x_min, gyro_x)
            self.r1_gyro_x_max = max(self.r1_gyro_x_max, gyro_x)
            self.r1_gyro_y_min = min(self.r1_gyro_y_min, gyro_y)
            self.r1_gyro_y_max = max(self.r1_gyro_y_max, gyro_y)
            self.r1_gyro_z_min = min(self.r1_gyro_z_min, gyro_z)
            self.r1_gyro_z_max = max(self.r1_gyro_z_max, gyro_z)
    
    def update_r2(self, accel_x, accel_y, accel_z, gyro_x, gyro_y, gyro_z):
        with self.lock:
            self.r2_accel_x_min = min(self.r2_accel_x_min, accel_x)
            self.r2_accel_x_max = max(self.r2_accel_x_max, accel_x)
            self.r2_accel_y_min = min(self.r2_accel_y_min, accel_y)
            self.r2_accel_y_max = max(self.r2_accel_y_max, accel_y)
            self.r2_accel_z_min = min(self.r2_accel_z_min, accel_z)
            self.r2_accel_z_max = max(self.r2_accel_z_max, accel_z)
            self.r2_gyro_x_min = min(self.r2_gyro_x_min, gyro_x)
            self.r2_gyro_x_max = max(self.r2_gyro_x_max, gyro_x)
            self.r2_gyro_y_min = min(self.r2_gyro_y_min, gyro_y)
            self.r2_gyro_y_max = max(self.r2_gyro_y_max, gyro_y)
            self.r2_gyro_z_min = min(self.r2_gyro_z_min, gyro_z)
            self.r2_gyro_z_max = max(self.r2_gyro_z_max, gyro_z)
    
    def update_tx(self, accel_x, accel_y, accel_z, gyro_x, gyro_y, gyro_z):
        with self.lock:
            self.tx_accel_x_min = min(self.tx_accel_x_min, accel_x)
            self.tx_accel_x_max = max(self.tx_accel_x_max, accel_x)
            self.tx_accel_y_min = min(self.tx_accel_y_min, accel_y)
            self.tx_accel_y_max = max(self.tx_accel_y_max, accel_y)
            self.tx_accel_z_min = min(self.tx_accel_z_min, accel_z)
            self.tx_accel_z_max = max(self.tx_accel_z_max, accel_z)
            self.tx_gyro_x_min = min(self.tx_gyro_x_min, gyro_x)
            self.tx_gyro_x_max = max(self.tx_gyro_x_max, gyro_x)
            self.tx_gyro_y_min = min(self.tx_gyro_y_min, gyro_y)
            self.tx_gyro_y_max = max(self.tx_gyro_y_max, gyro_y)
            self.tx_gyro_z_min = min(self.tx_gyro_z_min, gyro_z)
            self.tx_gyro_z_max = max(self.tx_gyro_z_max, gyro_z)
    
    def reset(self):
        with self.lock:
            # Reset all min/max values
            self.r1_accel_x_min = self.r1_accel_x_max = receiver1.accel_x
            self.r1_accel_y_min = self.r1_accel_y_max = receiver1.accel_y
            self.r1_accel_z_min = self.r1_accel_z_max = receiver1.accel_z
            self.r1_gyro_x_min = self.r1_gyro_x_max = receiver1.gyro_x
            self.r1_gyro_y_min = self.r1_gyro_y_max = receiver1.gyro_y
            self.r1_gyro_z_min = self.r1_gyro_z_max = receiver1.gyro_z
            
            self.r2_accel_x_min = self.r2_accel_x_max = receiver2.accel_x
            self.r2_accel_y_min = self.r2_accel_y_max = receiver2.accel_y
            self.r2_accel_z_min = self.r2_accel_z_max = receiver2.accel_z
            self.r2_gyro_x_min = self.r2_gyro_x_max = receiver2.gyro_x
            self.r2_gyro_y_min = self.r2_gyro_y_max = receiver2.gyro_y
            self.r2_gyro_z_min = self.r2_gyro_z_max = receiver2.gyro_z
            
            self.tx_accel_x_min = self.tx_accel_x_max = transmitter.accel_x
            self.tx_accel_y_min = self.tx_accel_y_max = transmitter.accel_y
            self.tx_accel_z_min = self.tx_accel_z_max = transmitter.accel_z
            self.tx_gyro_x_min = self.tx_gyro_x_max = transmitter.gyro_x
            self.tx_gyro_y_min = self.tx_gyro_y_max = transmitter.gyro_y
            self.tx_gyro_z_min = self.tx_gyro_z_max = transmitter.gyro_z

movement_monitor = MovementMonitor()

# ===== ACTIVITY DETECTION (wobble detection + session tracking) =====
WOBBLE_ACTIVE_THRESHOLD = 0.8
WOBBLE_IDLE_THRESHOLD   = 0.3
SESSION_TIMEOUT_S       = 60

class ActivityDetector:
    """Detects deliberate rocking via combined accel+gyro EMA, tracks play sessions."""

    # States
    IDLE    = "idle"
    ACTIVE  = "active"
    COOLING = "cooling"

    def __init__(self, rocker_id):
        self.rocker_id = rocker_id
        self._lock = threading.Lock()
        self.ema = 0.0
        self.state = self.IDLE
        self.session_active = False
        self.session_start_time = 0.0
        self.last_wobble_time = 0.0
        self.session_id = None
        self.peak_magnitude = 0.0
        self.wobble_seconds = 0.0
        self._last_active_tick = 0.0

    def update(self, ax, ay, az, gx, gy, gz):
        """Feed new sensor sample. Returns event string or None: 'session_start', 'session_end'."""
        now = time.time()
        accel_mag = abs(math.sqrt(ax * ax + ay * ay + az * az) - 9.81)
        gyro_mag = math.sqrt(gx * gx + gy * gy + gz * gz)
        combined = 0.4 * accel_mag + 0.6 * gyro_mag

        with self._lock:
            self.ema = 0.15 * combined + 0.85 * self.ema
            self.peak_magnitude = max(self.peak_magnitude, self.ema)

            event = None

            if self.state == self.IDLE:
                if self.ema >= WOBBLE_ACTIVE_THRESHOLD:
                    self.state = self.ACTIVE
                    self.session_active = True
                    self.session_start_time = now
                    self.last_wobble_time = now
                    self._last_active_tick = now
                    self.session_id = str(uuid.uuid4())
                    self.peak_magnitude = self.ema
                    self.wobble_seconds = 0.0
                    event = "session_start"
                    print(f"  [Activity] {self.rocker_id} session START (ema={self.ema:.2f})")

            elif self.state == self.ACTIVE:
                self.last_wobble_time = now
                # Accumulate active wobble time
                if self._last_active_tick:
                    self.wobble_seconds += now - self._last_active_tick
                self._last_active_tick = now
                if self.ema < WOBBLE_IDLE_THRESHOLD:
                    self.state = self.COOLING
                    self._last_active_tick = 0.0

            elif self.state == self.COOLING:
                if self.ema >= WOBBLE_ACTIVE_THRESHOLD:
                    self.state = self.ACTIVE
                    self.last_wobble_time = now
                    self._last_active_tick = now
                elif (now - self.last_wobble_time) >= SESSION_TIMEOUT_S:
                    event = self._end_session(now)

            return event

    def check_timeout(self):
        """Called from dashboard poll for offline rockers. Returns 'session_end' or None."""
        now = time.time()
        with self._lock:
            if self.state in (self.ACTIVE, self.COOLING):
                if (now - self.last_wobble_time) >= SESSION_TIMEOUT_S:
                    return self._end_session(now)
        return None

    def _end_session(self, now):
        """End the current session (must be called under lock). Returns 'session_end'."""
        # Snapshot final values BEFORE clearing state
        self._ended_duration = now - self.session_start_time
        self._ended_peak = self.peak_magnitude
        self._ended_wobble = self.wobble_seconds
        print(f"  [Activity] {self.rocker_id} session END (dur={self._ended_duration:.0f}s, peak={self._ended_peak:.2f}, wobble={self._ended_wobble:.0f}s)")
        self.state = self.IDLE
        self.session_active = False
        self._last_active_tick = 0.0
        return "session_end"

    def current_duration(self):
        """Return current session duration in seconds (0 if no active session)."""
        with self._lock:
            if self.session_active:
                return time.time() - self.session_start_time
            return 0.0

    def get_session_summary(self):
        """Return dict with session info for persistence."""
        with self._lock:
            if self.session_active:
                duration = time.time() - self.session_start_time
                peak = self.peak_magnitude
                wobble = self.wobble_seconds
            else:
                # Use values saved by _end_session
                duration = getattr(self, '_ended_duration', 0)
                peak = getattr(self, '_ended_peak', 0)
                wobble = getattr(self, '_ended_wobble', 0)
            return {
                "session_id": self.session_id,
                "rocker": self.rocker_id,
                "started_at": self.session_start_time,
                "duration_s": duration,
                "peak_magnitude": peak,
                "wobble_seconds": wobble,
            }

_activity_r1 = ActivityDetector("r1")
_activity_r2 = ActivityDetector("r2")
_activity_tx = ActivityDetector("tx")

def _on_activity_event(detector, event):
    """Handle session_start / session_end events (logging + Supabase persistence)."""
    summary = detector.get_session_summary()
    if event == "session_start":
        log_event(f"{detector.rocker_id} session start", "proximity")
        _supabase_insert_async("sessions", {
            "session_id": summary["session_id"],
            "rocker": summary["rocker"],
            "started_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(summary["started_at"])),
            "status": "active",
        })
    elif event == "session_end":
        log_event(f"{detector.rocker_id} session end ({summary['duration_s']:.0f}s)", "proximity")
        _supabase_update_async("sessions", "session_id", summary["session_id"], {
            "ended_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "duration_s": round(summary["duration_s"], 1),
            "peak_magnitude": round(summary["peak_magnitude"], 3),
            "wobble_seconds": round(summary["wobble_seconds"], 1),
            "status": "ended",
        })

class RockerState:
    def __init__(self, name):
        self.name = name
        self.accel_x = 0.0
        self.accel_y = 0.0
        self.accel_z = 0.0
        self.gyro_x = 0.0
        self.gyro_y = 0.0
        self.gyro_z = 0.0
        self.distance = 999.0
        self.in_range = False
        # Scene 1 flags
        self.is_close = False
        self.is_medium = False
        self.is_far = True
        # Scene 2 flags
        self.is_isolated = False
        self.last_bulb_trigger_time = 0
        self.last_state_change_time = 0
        self.assigned_bulb = None
        self.assigned_color = None
        
    def update_accel(self, x, y, z):
        self.accel_x = x
        self.accel_y = y
        self.accel_z = z
        
    def update_gyro(self, x, y, z):
        self.gyro_x = x
        self.gyro_y = y
        self.gyro_z = z
    
    def update_proximity_scene1(self, distance, in_range):
        """Update proximity for Scene 1 (multi-state distance) with hysteresis"""
        self.distance = distance
        self.in_range = in_range
        
        # Apply hysteresis to prevent flickering at boundaries
        # Current state determines which threshold to use
        
        if self.is_close:
            # Currently close - need to exceed close threshold + hysteresis to leave
            if distance > (CLOSE_THRESHOLD + HYSTERESIS):
                if distance >= FAR_THRESHOLD:
                    self.is_close = False
                    self.is_medium = False
                    self.is_far = True
                else:
                    self.is_close = False
                    self.is_medium = True
                    self.is_far = False
        elif self.is_far:
            # Currently far - need to drop below far threshold - hysteresis to leave
            if distance < (FAR_THRESHOLD - HYSTERESIS):
                if distance <= CLOSE_THRESHOLD:
                    self.is_close = True
                    self.is_medium = False
                    self.is_far = False
                else:
                    self.is_close = False
                    self.is_medium = True
                    self.is_far = False
        else:  # is_medium
            # Currently medium - check both boundaries with hysteresis
            if distance < (CLOSE_THRESHOLD - HYSTERESIS):
                self.is_close = True
                self.is_medium = False
                self.is_far = False
            elif distance > (FAR_THRESHOLD + HYSTERESIS):
                self.is_close = False
                self.is_medium = False
                self.is_far = True
    
    def update_proximity_scene2(self, distance, in_range):
        """Update proximity for Scene 2 (isolation mode)"""
        self.distance = distance
        self.in_range = in_range
        
        was_isolated = self.is_isolated
        
        if not self.is_isolated and distance > (ISOLATION_THRESHOLD + HYSTERESIS):
            self.is_isolated = True
            state_changed = True
        elif self.is_isolated and distance < (ISOLATION_THRESHOLD - HYSTERESIS):
            self.is_isolated = False
            state_changed = True
        else:
            state_changed = False
        
        if state_changed:
            current_time = time.time()
            if current_time - self.last_state_change_time < STATE_CHANGE_DEBOUNCE:
                self.is_isolated = was_isolated
                return False
            self.last_state_change_time = current_time
            return True
        
        return False

# Initialize rocker states
receiver1 = RockerState("Receiver1_Copper")
receiver2 = RockerState("Receiver2_White")
transmitter = RockerState("Transmitter_Purple")

# Backup rocker states (parallel to primary — always receiving, only active source drives logic)
receiver1_backup = RockerState("Receiver1_Copper_B")
receiver2_backup = RockerState("Receiver2_White_B")
transmitter_backup = RockerState("Transmitter_Purple_B")

# ===== ACTIVE SOURCE GETTERS =====
def get_r1():
    return receiver1_backup if r1_use_backup else receiver1

def get_r2():
    return receiver2_backup if r2_use_backup else receiver2

def get_tx():
    return transmitter_backup if tx_use_backup else transmitter

# Scene state
current_scene = 0  # 0, 1, or 2
scene_lock = threading.Lock()

# Scene 0 state (only uses R1 - Copper rocker)
class Scene0State:
    def __init__(self):
        self.r1_is_close = None  # None = uninitialized, True = close, False = far
        self.r1_last_change_time = 0
        self.last_light_change_time = 0

scene0_state = Scene0State()
SCENE0_HYSTERESIS = 0.15  # 15cm hysteresis buffer
SCENE0_DEBOUNCE = 0.5     # 500ms debounce

# Scene 1 state
last_trigger_time_scene1 = 0
last_state_scene1 = None
trigger_lock_scene1 = threading.Lock()

# Scene 2 state
bulb_lock = threading.Lock()

# ===== DASHBOARD STATE (Phase 1) =====
last_seen = {"r1": 0.0, "r2": 0.0, "tx": 0.0}
last_osc_time = {}           # port_number (int) -> float timestamp
CONNECTION_TIMEOUT = 2.0
OSC_ACTIVITY_WINDOW = 0.15   # seconds a dot stays lit after a message

# 4 bulbs mirroring HUE_LIGHTS order; updated whenever a Hue command fires
bulb_display_state = [
    {"color": "warm_white", "on": True},
    {"color": "warm_white", "on": True},
    {"color": "warm_white", "on": True},
    {"color": "warm_white", "on": True},
]
_dash = {}   # widget references populated by _build_dashboard()
_root = None  # set in create_gui(); needed for root.after() calls from threads
_pusher_client = None  # initialised in main() if PUSHER_ENABLED

# Timeout tracking (Step 10)
_timeout_logged       = {"r1": False, "r2": False, "tx": False}
_all_timeout_triggered = False

def _color_to_hex(name):
    """Map Hue color token to an approximate display hex color"""
    _table = {
        "warm_white": "#ffcc88", "cool_white": "#ccdeff",
        "red":        "#ff4444", "blue":       "#4499ff",
        "green":      "#44ff88", "yellow":     "#ffee44",
        "orange":     "#ffaa44", "purple":     "#cc66ff",
        "pink":       "#ff88cc", "white":      "#ffffff",
        "cyan":       "#44ffee", "magenta":    "#ff44cc",
        "aqua":       "#44ffee", "fuchsia":    "#ff44cc",
        "lime":       "#88ff44", "teal":       "#44aaaa",
        "navy":       "#003388", "maroon":     "#880000",
        "olive":      "#888800", "coral":      "#ff7755",
        "turquoise":  "#44ddbb", "violet":     "#ee44ff",
        "gold":       "#ffcc00", "silver":     "#cccccc",
        "indigo":     "#4400aa", "crimson":    "#cc1133",
        "salmon":     "#ff8877", "khaki":      "#ccbb55",
    }
    key = str(name).lower().replace(" ", "_")
    return _table.get(key, "#888888")

# VCV Rack output clients
vcv_client = SimpleUDPClient("192.168.50.201", VCV_RACK_PORT)

# GUI variables
status_label = None
r1_label = None
r2_label = None
scene_btns = {}       # {0: btn, 1: btn, 2: btn}
context_label = None  # scene state panel (Phase 2)
event_log = None      # tk.Text event log (Phase 2)

# Scene button styling constants
SCENE_COLORS = {0: "#FFD700", 1: "#87CEEB", 2: "#98FB98"}
SCENE_DIM    = {0: "#c8a800", 1: "#5a9ab5", 2: "#6ab56a"}
SCENE_NAMES  = {0: "Individual Layers", 1: "Distance States", 2: "Isolation Mode"}

def log_event(msg, tag="info"):
    """Append a timestamped line to the event log widget"""
    if event_log is None:
        return
    ts = time.strftime("%H:%M:%S")
    event_log.config(state=tk.NORMAL)
    event_log.insert(tk.END, f"{ts} — {msg}\n", tag)
    event_log.see(tk.END)
    # Trim to 8 visible lines
    lines = int(event_log.index(tk.END).split(".")[0]) - 1
    if lines > 8:
        event_log.delete("1.0", f"{lines - 8}.0")
    event_log.config(state=tk.DISABLED)

# ===== THRESHOLD SLIDER CALLBACKS (Phase 3, Step 8) =====
def _set_close_threshold(val):
    global CLOSE_THRESHOLD
    CLOSE_THRESHOLD = float(val)

def _set_far_threshold(val):
    global FAR_THRESHOLD
    FAR_THRESHOLD = float(val)

def _set_hysteresis(val):
    global HYSTERESIS
    HYSTERESIS = float(val)

def _set_wobble_active(val):
    global WOBBLE_ACTIVE_THRESHOLD
    WOBBLE_ACTIVE_THRESHOLD = float(val)

def _set_wobble_idle(val):
    global WOBBLE_IDLE_THRESHOLD
    WOBBLE_IDLE_THRESHOLD = float(val)

def _set_session_timeout(val):
    global SESSION_TIMEOUT_S
    SESSION_TIMEOUT_S = float(val)

# ===== HUE LIGHT CONTROL =====
def run_hue_command(command_list, description):
    """Execute an OpenHue command"""
    try:
        result = subprocess.run(
            command_list,
            capture_output=True,
            text=True,
            timeout=10
        )
        
        if result.returncode == 0:
            print(f"   ✓ {description}")
        else:
            print(f"   ✗ {description} - Failed")
                
    except subprocess.TimeoutExpired:
        print(f"   ✗ {description} - Timeout")
    except FileNotFoundError:
        print(f"   ✗ 'openhue' not found. Install from: https://github.com/openhue/openhue-cli")
    except Exception as e:
        print(f"   ✗ {description} - Error: {e}")

# ===== SCENE 0 FUNCTIONS =====
def scene0_update_proximity(distance):
    """Update proximity state for R1 (Copper) with hysteresis and debouncing
    
    Args:
        distance: Current distance in meters
    
    Returns:
        True if state changed, False otherwise
    """
    global scene0_state
    current_time = time.time()
    
    current_state = scene0_state.r1_is_close
    
    # Determine new state with hysteresis
    new_state = None
    
    if current_state is None:
        # First reading - initialize based on threshold
        new_state = distance <= CLOSE_THRESHOLD
    elif current_state:  # Currently close
        # Need to cross threshold + hysteresis to become far
        if distance > (CLOSE_THRESHOLD + SCENE0_HYSTERESIS):
            new_state = False
        else:
            new_state = True
    else:  # Currently far
        # Need to cross threshold - hysteresis to become close
        if distance < (CLOSE_THRESHOLD - SCENE0_HYSTERESIS):
            new_state = True
        else:
            new_state = False
    
    # Check if state changed
    if new_state != current_state:
        # Apply debounce
        if current_time - scene0_state.r1_last_change_time < SCENE0_DEBOUNCE:
            return False  # Too soon, ignore
        
        # State change confirmed
        scene0_state.r1_is_close = new_state
        scene0_state.r1_last_change_time = current_time
        
        # Also apply debounce to light changes
        if current_time - scene0_state.last_light_change_time < SCENE0_DEBOUNCE:
            print(f"  [R1 Copper] Proximity changed: {'CLOSE' if new_state else 'FAR'} ({distance:.2f}m) [debounced]")
            return False
        
        scene0_state.last_light_change_time = current_time
        
        # Trigger lights
        if new_state:
            print("\n🟡 SCENE 0: R1 CLOSE - Warm white (t500)")
            print(f"  R1 (Copper): {distance:.2f}m")
            run_hue_command(
                ["openhue", "set", "room", HUE_ROOM_ID, "--on", "-t", "500", "--transition-time", "5s"],
                "Warm white (t500)"
            )
            for s in bulb_display_state: s.update({"color": "warm_white", "on": True})
            log_event("R1 CLOSE → Warm white", "proximity")
        else:
            print("\n⚪ SCENE 0: R1 FAR - Cool white (t153)")
            print(f"  R1 (Copper): {distance:.2f}m")
            run_hue_command(
                ["openhue", "set", "room", HUE_ROOM_ID, "--on", "-t", "153", "--transition-time", "5s"],
                "Cool white (t153)"
            )
            for s in bulb_display_state: s.update({"color": "cool_white", "on": True})
            log_event("R1 FAR → Cool white", "proximity")

        return True
    
    return False

# ===== SCENE 1 FUNCTIONS =====
def scene1_trigger_both_close():
    """Scene 1: Both receivers close (≤0.8m)"""
    print(f"\n🟡 SCENE 1: BOTH CLOSE - Warm white (t500)")
    run_hue_command(
        ["openhue", "set", "room", HUE_ROOM_ID, "--on", "-t", "500", "--transition-time", "5s"],
        "Warm white (t500)"
    )
    for s in bulb_display_state: s.update({"color": "warm_white", "on": True})
    log_event("BOTH CLOSE → Warm white", "light")

def scene1_trigger_r1_far():
    """Scene 1: Receiver1 (Copper) far"""
    print(f"\n🔵 SCENE 1: R1 FAR - Blue")
    run_hue_command(
        ["openhue", "set", "room", HUE_ROOM_ID, "--on", "--color", "blue", "--transition-time", "5s"],
        "Blue (R1 far)"
    )
    for s in bulb_display_state: s.update({"color": "blue", "on": True})
    log_event("R1 FAR → Blue", "light")

def scene1_trigger_r2_far():
    """Scene 1: Receiver2 (White) far"""
    print(f"\n⚪ SCENE 1: R2 FAR - Cool white (t153)")
    run_hue_command(
        ["openhue", "set", "room", HUE_ROOM_ID, "--on", "-t", "153", "--transition-time", "5s"],
        "Cool white (t153)"
    )
    for s in bulb_display_state: s.update({"color": "cool_white", "on": True})
    log_event("R2 FAR → Cool white", "light")

def scene1_trigger_both_far():
    """Scene 1: Both receivers very far (≥2.0m)"""
    print(f"\n🔴 SCENE 1: BOTH FAR - Red")
    run_hue_command(
        ["openhue", "set", "room", HUE_ROOM_ID, "--on", "--color", "red", "--transition-time", "5s"],
        "Red (both far)"
    )
    for s in bulb_display_state: s.update({"color": "red", "on": True})
    log_event("BOTH FAR → Red", "light")

def scene1_check_distance_triggers():
    """Evaluate Scene 1 distance thresholds"""
    global last_trigger_time_scene1, last_state_scene1
    
    current_time = time.time()
    current_state = None
    
    # Priority order for state determination (use active source)
    r1 = get_r1()
    r2 = get_r2()
    if r1.is_close and r2.is_close:
        current_state = "both_close"
    elif not r1.is_close and not r2.is_close:
        current_state = "both_far"  # Both beyond threshold
    elif not r1.is_close and r2.is_close:
        current_state = "r1_far"
    elif r1.is_close and not r2.is_close:
        current_state = "r2_far"
    
    if current_state and current_state != last_state_scene1:
        with trigger_lock_scene1:
            if current_time - last_trigger_time_scene1 < TRIGGER_COOLDOWN:
                return
            last_trigger_time_scene1 = current_time
            last_state_scene1 = current_state
        
        if current_state == "both_far":
            scene1_trigger_both_far()
        elif current_state == "both_close":
            scene1_trigger_both_close()
        elif current_state == "r1_far":
            scene1_trigger_r1_far()
        elif current_state == "r2_far":
            scene1_trigger_r2_far()

# ===== SCENE 2 FUNCTIONS =====
def scene2_trigger_random_bulb(rocker_name):
    """Scene 2: Change random bulb when rocker isolated"""
    current_time = time.time()
    rocker = get_r1() if "R1" in rocker_name or "Copper" in rocker_name else get_r2()
    
    if not rocker.is_isolated:
        return
    
    with bulb_lock:
        if current_time - rocker.last_bulb_trigger_time < TRIGGER_COOLDOWN:
            return
        rocker.last_bulb_trigger_time = current_time
    
    other_rocker = get_r2() if rocker == get_r1() else get_r1()
    available_bulbs = [b for b in HUE_LIGHTS if b != other_rocker.assigned_bulb]
    
    if not available_bulbs:
        return
    
    random_bulb = random.choice(available_bulbs)
    random_color = random.choice(RANDOM_COLORS)
    
    rocker.assigned_bulb = random_bulb
    rocker.assigned_color = random_color

    _b_idx = next((i for i, b in enumerate(HUE_LIGHTS) if b["id"] == random_bulb["id"]), None)
    if _b_idx is not None:
        bulb_display_state[_b_idx] = {"color": random_color, "on": True}

    log_event(f"{rocker_name} isolated → {random_bulb['name']} {random_color}", "light")
    print(f"\n💡 SCENE 2: {rocker_name} ISOLATED - {random_bulb['name']} → {random_color}")
    trigger_key = "r1_isolated" if ("R1" in rocker_name or "Copper" in rocker_name) else "r2_isolated"
    broadcast_trigger(trigger_key, color=random_color, bulb=random_bulb["name"])

    run_hue_command(
        ["openhue", "set", "light", random_bulb["id"], "--on", "--color", random_color, "--transition-time", "2s"],
        f"{random_bulb['name']} → {random_color}"
    )

def scene2_reset_bulb(rocker_name):
    """Scene 2: Reset bulb when rocker returns"""
    rocker = get_r1() if "R1" in rocker_name or "Copper" in rocker_name else get_r2()
    
    if rocker.assigned_bulb is None:
        return

    _b_idx = next((i for i, b in enumerate(HUE_LIGHTS) if b["id"] == rocker.assigned_bulb["id"]), None)

    print(f"\n🔄 SCENE 2: {rocker_name} RETURNED - {rocker.assigned_bulb['name']} → Warm white (t500)")

    run_hue_command(
        ["openhue", "set", "light", rocker.assigned_bulb["id"], "--on", "-t", "500", "--transition-time", "3s"],
        f"{rocker.assigned_bulb['name']} → Warm white"
    )

    if _b_idx is not None:
        bulb_display_state[_b_idx] = {"color": "warm_white", "on": True}

    log_event(f"{rocker_name} returned → warm white", "light")
    return_key = "r1_returned" if ("R1" in rocker_name or "Copper" in rocker_name) else "r2_returned"
    broadcast_trigger(return_key)
    rocker.assigned_bulb = None
    rocker.assigned_color = None

# ===== OSC HANDLERS - RECEIVER 1 (COPPER) =====
def r1_accel_x_handler(unused_addr, x):
    receiver1.accel_x = x
    if r1_use_backup:
        return
    with scene_lock:
        scene = current_scene
    if scene in (0, 1) or (scene == 2 and receiver1.is_isolated):
        vcv_client.send_message("/r1/accel/x", x)

def r1_accel_y_handler(unused_addr, y):
    receiver1.accel_y = y
    if r1_use_backup:
        return
    with scene_lock:
        scene = current_scene
    if scene in (0, 1) or (scene == 2 and receiver1.is_isolated):
        vcv_client.send_message("/r1/accel/y", y)

def r1_accel_z_handler(unused_addr, z):
    last_osc_time[R1_SENSOR_PORT] = time.time()
    receiver1.accel_z = z
    receiver1.update_accel(receiver1.accel_x, receiver1.accel_y, receiver1.accel_z)
    if r1_use_backup:
        return
    last_seen["r1"] = time.time()
    movement_monitor.update_r1(
        receiver1.accel_x, receiver1.accel_y, receiver1.accel_z,
        receiver1.gyro_x, receiver1.gyro_y, receiver1.gyro_z
    )
    _activity_event = _activity_r1.update(
        receiver1.accel_x, receiver1.accel_y, receiver1.accel_z,
        receiver1.gyro_x, receiver1.gyro_y, receiver1.gyro_z
    )
    if _activity_event:
        _on_activity_event(_activity_r1, _activity_event)
    with scene_lock:
        scene = current_scene
    if scene in (0, 1) or (scene == 2 and receiver1.is_isolated):
        vcv_client.send_message("/r1/accel/z", z)

def r1_gyro_x_handler(unused_addr, x):
    receiver1.gyro_x = x
    if r1_use_backup:
        return
    with scene_lock:
        scene = current_scene
    if scene in (0, 1) or (scene == 2 and receiver1.is_isolated):
        vcv_client.send_message("/r1/gyro/x", x)

def r1_gyro_y_handler(unused_addr, y):
    receiver1.gyro_y = y
    if r1_use_backup:
        return
    with scene_lock:
        scene = current_scene
    if scene in (0, 1) or (scene == 2 and receiver1.is_isolated):
        vcv_client.send_message("/r1/gyro/y", y)

def r1_gyro_z_handler(unused_addr, z):
    receiver1.gyro_z = z
    if r1_use_backup:
        return
    with scene_lock:
        scene = current_scene
    if scene in (0, 1) or (scene == 2 and receiver1.is_isolated):
        vcv_client.send_message("/r1/gyro/z", z)

def r1_proximity_handler(unused_addr, distance, in_range):
    last_osc_time[R1_PROXIMITY_PORT] = time.time()
    receiver1.distance = distance
    receiver1.in_range = in_range
    if r1_use_backup:
        return
    last_seen["r1"] = time.time()
    with scene_lock:
        scene = current_scene
    if scene == 0:
        scene0_update_proximity(distance)
        vcv_client.send_message("/r1/proximity/distance", distance)
    elif scene == 1:
        receiver1.update_proximity_scene1(distance, in_range)
        vcv_client.send_message("/r1/proximity/distance", distance)
        scene1_check_distance_triggers()
    elif scene == 2:
        state_changed = receiver1.update_proximity_scene2(distance, in_range)
        if receiver1.is_isolated:
            vcv_client.send_message("/r1/proximity/distance", distance)
        if state_changed and receiver1.is_isolated:
            vcv_client.send_message("/r1/solo", 1)
            scene2_trigger_random_bulb("R1 (Copper)")
        if state_changed and not receiver1.is_isolated:
            vcv_client.send_message("/r1/solo", 0)
            scene2_reset_bulb("R1 (Copper)")
    update_gui_status()

# ===== OSC HANDLERS - RECEIVER 2 (WHITE) =====
def r2_accel_x_handler(unused_addr, x):
    receiver2.accel_x = x
    if r2_use_backup:
        return
    with scene_lock:
        scene = current_scene
    if scene == 1:
        vcv_client.send_message("/r2/accel/x", x)
    elif scene == 2 and receiver2.is_isolated:
        vcv_client.send_message("/r2/accel/x", x)

def r2_accel_y_handler(unused_addr, y):
    receiver2.accel_y = y
    if r2_use_backup:
        return
    with scene_lock:
        scene = current_scene
    if scene == 1:
        vcv_client.send_message("/r2/accel/y", y)
    elif scene == 2 and receiver2.is_isolated:
        vcv_client.send_message("/r2/accel/y", y)

def r2_accel_z_handler(unused_addr, z):
    last_osc_time[R2_SENSOR_PORT] = time.time()
    receiver2.accel_z = z
    receiver2.update_accel(receiver2.accel_x, receiver2.accel_y, receiver2.accel_z)
    if r2_use_backup:
        return
    last_seen["r2"] = time.time()
    movement_monitor.update_r2(
        receiver2.accel_x, receiver2.accel_y, receiver2.accel_z,
        receiver2.gyro_x, receiver2.gyro_y, receiver2.gyro_z
    )
    _activity_event = _activity_r2.update(
        receiver2.accel_x, receiver2.accel_y, receiver2.accel_z,
        receiver2.gyro_x, receiver2.gyro_y, receiver2.gyro_z
    )
    if _activity_event:
        _on_activity_event(_activity_r2, _activity_event)
    with scene_lock:
        scene = current_scene
    if scene == 1:
        vcv_client.send_message("/r2/accel/z", z)
    elif scene == 2 and receiver2.is_isolated:
        vcv_client.send_message("/r2/accel/z", z)

def r2_gyro_x_handler(unused_addr, x):
    receiver2.gyro_x = x
    if r2_use_backup:
        return
    with scene_lock:
        scene = current_scene
    if scene == 1:
        vcv_client.send_message("/r2/gyro/x", x)
    elif scene == 2 and receiver2.is_isolated:
        vcv_client.send_message("/r2/gyro/x", x)

def r2_gyro_y_handler(unused_addr, y):
    receiver2.gyro_y = y
    if r2_use_backup:
        return
    with scene_lock:
        scene = current_scene
    if scene == 1:
        vcv_client.send_message("/r2/gyro/y", y)
    elif scene == 2 and receiver2.is_isolated:
        vcv_client.send_message("/r2/gyro/y", y)

def r2_gyro_z_handler(unused_addr, z):
    receiver2.gyro_z = z
    if r2_use_backup:
        return
    with scene_lock:
        scene = current_scene
    if scene == 1:
        vcv_client.send_message("/r2/gyro/z", z)
    elif scene == 2 and receiver2.is_isolated:
        vcv_client.send_message("/r2/gyro/z", z)

def r2_proximity_handler(unused_addr, distance, in_range):
    last_osc_time[R2_PROXIMITY_PORT] = time.time()
    receiver2.distance = distance
    receiver2.in_range = in_range
    if r2_use_backup:
        return
    last_seen["r2"] = time.time()
    with scene_lock:
        scene = current_scene
    if scene == 0:
        pass  # R2 not used in Scene 0
    elif scene == 1:
        receiver2.update_proximity_scene1(distance, in_range)
        vcv_client.send_message("/r2/proximity/distance", distance)
        scene1_check_distance_triggers()
    elif scene == 2:
        state_changed = receiver2.update_proximity_scene2(distance, in_range)
        if receiver2.is_isolated:
            vcv_client.send_message("/r2/proximity/distance", distance)
        if state_changed and receiver2.is_isolated:
            vcv_client.send_message("/r2/solo", 1)
            scene2_trigger_random_bulb("R2 (White)")
        if state_changed and not receiver2.is_isolated:
            vcv_client.send_message("/r2/solo", 0)
            scene2_reset_bulb("R2 (White)")
    update_gui_status()

# ===== OSC HANDLERS - TRANSMITTER (PURPLE) =====
def transmitter_accel_x_handler(unused_addr, x):
    transmitter.accel_x = x
    if tx_use_backup:
        return
    vcv_client.send_message("/transmitter/accel/x", x)

def transmitter_accel_y_handler(unused_addr, y):
    transmitter.accel_y = y
    if tx_use_backup:
        return
    vcv_client.send_message("/transmitter/accel/y", y)

def transmitter_accel_z_handler(unused_addr, z):
    last_osc_time[TRANSMITTER_PORT] = time.time()
    transmitter.accel_z = z
    if tx_use_backup:
        return
    last_seen["tx"] = time.time()
    vcv_client.send_message("/transmitter/accel/z", z)
    last_osc_time[VCV_RACK_PORT] = time.time()
    movement_monitor.update_tx(
        transmitter.accel_x, transmitter.accel_y, transmitter.accel_z,
        transmitter.gyro_x, transmitter.gyro_y, transmitter.gyro_z
    )
    _activity_event = _activity_tx.update(
        transmitter.accel_x, transmitter.accel_y, transmitter.accel_z,
        transmitter.gyro_x, transmitter.gyro_y, transmitter.gyro_z
    )
    if _activity_event:
        _on_activity_event(_activity_tx, _activity_event)

def transmitter_gyro_x_handler(unused_addr, x):
    transmitter.gyro_x = x
    if tx_use_backup:
        return
    vcv_client.send_message("/transmitter/gyro/x", x)

def transmitter_gyro_y_handler(unused_addr, y):
    transmitter.gyro_y = y
    if tx_use_backup:
        return
    vcv_client.send_message("/transmitter/gyro/y", y)

def transmitter_gyro_z_handler(unused_addr, z):
    transmitter.gyro_z = z
    if tx_use_backup:
        return
    vcv_client.send_message("/transmitter/gyro/z", z)

# ===== OSC HANDLERS - RECEIVER 1 BACKUP (COPPER B) =====
def r1b_accel_x_handler(unused_addr, x):
    receiver1_backup.accel_x = x
    if not r1_use_backup:
        return
    with scene_lock:
        scene = current_scene
    if scene in (0, 1) or (scene == 2 and receiver1_backup.is_isolated):
        vcv_client.send_message("/r1/accel/x", x)

def r1b_accel_y_handler(unused_addr, y):
    receiver1_backup.accel_y = y
    if not r1_use_backup:
        return
    with scene_lock:
        scene = current_scene
    if scene in (0, 1) or (scene == 2 and receiver1_backup.is_isolated):
        vcv_client.send_message("/r1/accel/y", y)

def r1b_accel_z_handler(unused_addr, z):
    receiver1_backup.accel_z = z
    receiver1_backup.update_accel(receiver1_backup.accel_x, receiver1_backup.accel_y, receiver1_backup.accel_z)
    if not r1_use_backup:
        return
    last_seen["r1"] = time.time()
    movement_monitor.update_r1(
        receiver1_backup.accel_x, receiver1_backup.accel_y, receiver1_backup.accel_z,
        receiver1_backup.gyro_x, receiver1_backup.gyro_y, receiver1_backup.gyro_z
    )
    _activity_event = _activity_r1.update(
        receiver1_backup.accel_x, receiver1_backup.accel_y, receiver1_backup.accel_z,
        receiver1_backup.gyro_x, receiver1_backup.gyro_y, receiver1_backup.gyro_z
    )
    if _activity_event:
        _on_activity_event(_activity_r1, _activity_event)
    with scene_lock:
        scene = current_scene
    if scene in (0, 1) or (scene == 2 and receiver1_backup.is_isolated):
        vcv_client.send_message("/r1/accel/z", z)

def r1b_gyro_x_handler(unused_addr, x):
    receiver1_backup.gyro_x = x
    if not r1_use_backup:
        return
    with scene_lock:
        scene = current_scene
    if scene in (0, 1) or (scene == 2 and receiver1_backup.is_isolated):
        vcv_client.send_message("/r1/gyro/x", x)

def r1b_gyro_y_handler(unused_addr, y):
    receiver1_backup.gyro_y = y
    if not r1_use_backup:
        return
    with scene_lock:
        scene = current_scene
    if scene in (0, 1) or (scene == 2 and receiver1_backup.is_isolated):
        vcv_client.send_message("/r1/gyro/y", y)

def r1b_gyro_z_handler(unused_addr, z):
    receiver1_backup.gyro_z = z
    if not r1_use_backup:
        return
    with scene_lock:
        scene = current_scene
    if scene in (0, 1) or (scene == 2 and receiver1_backup.is_isolated):
        vcv_client.send_message("/r1/gyro/z", z)

def r1b_proximity_handler(unused_addr, distance, in_range):
    receiver1_backup.distance = distance
    receiver1_backup.in_range = in_range
    if not r1_use_backup:
        return
    last_seen["r1"] = time.time()
    with scene_lock:
        scene = current_scene
    if scene == 0:
        scene0_update_proximity(distance)
        vcv_client.send_message("/r1/proximity/distance", distance)
    elif scene == 1:
        receiver1_backup.update_proximity_scene1(distance, in_range)
        vcv_client.send_message("/r1/proximity/distance", distance)
        scene1_check_distance_triggers()
    elif scene == 2:
        state_changed = receiver1_backup.update_proximity_scene2(distance, in_range)
        if receiver1_backup.is_isolated:
            vcv_client.send_message("/r1/proximity/distance", distance)
        if state_changed and receiver1_backup.is_isolated:
            vcv_client.send_message("/r1/solo", 1)
            scene2_trigger_random_bulb("R1 (Copper)")
        if state_changed and not receiver1_backup.is_isolated:
            vcv_client.send_message("/r1/solo", 0)
            scene2_reset_bulb("R1 (Copper)")
    update_gui_status()

# ===== OSC HANDLERS - RECEIVER 2 BACKUP (WHITE B) =====
def r2b_accel_x_handler(unused_addr, x):
    receiver2_backup.accel_x = x
    if not r2_use_backup:
        return
    with scene_lock:
        scene = current_scene
    if scene == 1:
        vcv_client.send_message("/r2/accel/x", x)
    elif scene == 2 and receiver2_backup.is_isolated:
        vcv_client.send_message("/r2/accel/x", x)

def r2b_accel_y_handler(unused_addr, y):
    receiver2_backup.accel_y = y
    if not r2_use_backup:
        return
    with scene_lock:
        scene = current_scene
    if scene == 1:
        vcv_client.send_message("/r2/accel/y", y)
    elif scene == 2 and receiver2_backup.is_isolated:
        vcv_client.send_message("/r2/accel/y", y)

def r2b_accel_z_handler(unused_addr, z):
    receiver2_backup.accel_z = z
    receiver2_backup.update_accel(receiver2_backup.accel_x, receiver2_backup.accel_y, receiver2_backup.accel_z)
    if not r2_use_backup:
        return
    last_seen["r2"] = time.time()
    movement_monitor.update_r2(
        receiver2_backup.accel_x, receiver2_backup.accel_y, receiver2_backup.accel_z,
        receiver2_backup.gyro_x, receiver2_backup.gyro_y, receiver2_backup.gyro_z
    )
    _activity_event = _activity_r2.update(
        receiver2_backup.accel_x, receiver2_backup.accel_y, receiver2_backup.accel_z,
        receiver2_backup.gyro_x, receiver2_backup.gyro_y, receiver2_backup.gyro_z
    )
    if _activity_event:
        _on_activity_event(_activity_r2, _activity_event)
    with scene_lock:
        scene = current_scene
    if scene == 1:
        vcv_client.send_message("/r2/accel/z", z)
    elif scene == 2 and receiver2_backup.is_isolated:
        vcv_client.send_message("/r2/accel/z", z)

def r2b_gyro_x_handler(unused_addr, x):
    receiver2_backup.gyro_x = x
    if not r2_use_backup:
        return
    with scene_lock:
        scene = current_scene
    if scene == 1:
        vcv_client.send_message("/r2/gyro/x", x)
    elif scene == 2 and receiver2_backup.is_isolated:
        vcv_client.send_message("/r2/gyro/x", x)

def r2b_gyro_y_handler(unused_addr, y):
    receiver2_backup.gyro_y = y
    if not r2_use_backup:
        return
    with scene_lock:
        scene = current_scene
    if scene == 1:
        vcv_client.send_message("/r2/gyro/y", y)
    elif scene == 2 and receiver2_backup.is_isolated:
        vcv_client.send_message("/r2/gyro/y", y)

def r2b_gyro_z_handler(unused_addr, z):
    receiver2_backup.gyro_z = z
    if not r2_use_backup:
        return
    with scene_lock:
        scene = current_scene
    if scene == 1:
        vcv_client.send_message("/r2/gyro/z", z)
    elif scene == 2 and receiver2_backup.is_isolated:
        vcv_client.send_message("/r2/gyro/z", z)

def r2b_proximity_handler(unused_addr, distance, in_range):
    receiver2_backup.distance = distance
    receiver2_backup.in_range = in_range
    if not r2_use_backup:
        return
    last_seen["r2"] = time.time()
    with scene_lock:
        scene = current_scene
    if scene == 0:
        pass  # R2 not used in Scene 0
    elif scene == 1:
        receiver2_backup.update_proximity_scene1(distance, in_range)
        vcv_client.send_message("/r2/proximity/distance", distance)
        scene1_check_distance_triggers()
    elif scene == 2:
        state_changed = receiver2_backup.update_proximity_scene2(distance, in_range)
        if receiver2_backup.is_isolated:
            vcv_client.send_message("/r2/proximity/distance", distance)
        if state_changed and receiver2_backup.is_isolated:
            vcv_client.send_message("/r2/solo", 1)
            scene2_trigger_random_bulb("R2 (White)")
        if state_changed and not receiver2_backup.is_isolated:
            vcv_client.send_message("/r2/solo", 0)
            scene2_reset_bulb("R2 (White)")
    update_gui_status()

# ===== OSC HANDLERS - TRANSMITTER BACKUP (PURPLE B) =====
def txb_accel_x_handler(unused_addr, x):
    transmitter_backup.accel_x = x
    if not tx_use_backup:
        return
    vcv_client.send_message("/transmitter/accel/x", x)

def txb_accel_y_handler(unused_addr, y):
    transmitter_backup.accel_y = y
    if not tx_use_backup:
        return
    vcv_client.send_message("/transmitter/accel/y", y)

def txb_accel_z_handler(unused_addr, z):
    transmitter_backup.accel_z = z
    if not tx_use_backup:
        return
    last_seen["tx"] = time.time()
    vcv_client.send_message("/transmitter/accel/z", z)
    movement_monitor.update_tx(
        transmitter_backup.accel_x, transmitter_backup.accel_y, transmitter_backup.accel_z,
        transmitter_backup.gyro_x, transmitter_backup.gyro_y, transmitter_backup.gyro_z
    )
    _activity_event = _activity_tx.update(
        transmitter_backup.accel_x, transmitter_backup.accel_y, transmitter_backup.accel_z,
        transmitter_backup.gyro_x, transmitter_backup.gyro_y, transmitter_backup.gyro_z
    )
    if _activity_event:
        _on_activity_event(_activity_tx, _activity_event)

def txb_gyro_x_handler(unused_addr, x):
    transmitter_backup.gyro_x = x
    if not tx_use_backup:
        return
    vcv_client.send_message("/transmitter/gyro/x", x)

def txb_gyro_y_handler(unused_addr, y):
    transmitter_backup.gyro_y = y
    if not tx_use_backup:
        return
    vcv_client.send_message("/transmitter/gyro/y", y)

def txb_gyro_z_handler(unused_addr, z):
    transmitter_backup.gyro_z = z
    if not tx_use_backup:
        return
    vcv_client.send_message("/transmitter/gyro/z", z)

# ===== GUI FUNCTIONS =====
def update_gui_status():
    """Update GUI with current rocker states"""
    global status_label, r1_label, r2_label
    
    if status_label:
        with scene_lock:
            scene = current_scene
        
        status_text = f"Active Scene: {scene}\n"
        
        if scene == 0:
            status_text += "Mode: Individual Layer Control"
        elif scene == 1:
            status_text += "Mode: Distance-Based Multi-State"
        elif scene == 2:
            status_text += "Mode: Individual Isolation"
        
        status_label.config(text=status_text)
    
    if r1_label:
        r1_src = get_r1()
        r1_text = f"Receiver 1 (Copper) [{'BACKUP' if r1_use_backup else 'PRIMARY'}]\n"
        r1_text += f"Distance: {r1_src.distance:.2f}m\n"

        with scene_lock:
            scene = current_scene

        if scene == 2:
            r1_text += f"Isolated: {'Yes' if r1_src.is_isolated else 'No'}\n"
            if r1_src.assigned_bulb:
                r1_text += f"Bulb: {r1_src.assigned_bulb['name']}"

        r1_label.config(text=r1_text)

    if r2_label:
        r2_src = get_r2()
        r2_text = f"Receiver 2 (White) [{'BACKUP' if r2_use_backup else 'PRIMARY'}]\n"
        r2_text += f"Distance: {r2_src.distance:.2f}m\n"

        with scene_lock:
            scene = current_scene

        if scene == 2:
            r2_text += f"Isolated: {'Yes' if r2_src.is_isolated else 'No'}\n"
            if r2_src.assigned_bulb:
                r2_text += f"Bulb: {r2_src.assigned_bulb['name']}"

        r2_label.config(text=r2_text)

    update_context_panel()

def switch_to_scene(scene_num):
    """Switch to a different scene"""
    global current_scene

    with scene_lock:
        if current_scene == scene_num:
            return

        old_scene = current_scene
        print(f"\n{'='*60}")
        print(f"SWITCHING FROM SCENE {old_scene} → SCENE {scene_num}")
        print(f"{'='*60}")

        current_scene = scene_num
        _update_scene_buttons(scene_num)
        log_event(f"Scene {scene_num}: {SCENE_NAMES[scene_num]}", "scene")
        broadcast_trigger("scene_change", scene=scene_num, name=SCENE_NAMES[scene_num])
        _supabase_insert_async("events", {
            "type": "scene_change",
            "scene": scene_num,
            "scene_name": SCENE_NAMES[scene_num],
            "detail": {"from_scene": old_scene},
        })

        # Brief "Switching..." indicator (Step 9)
        if context_label:
            context_label.config(text="Switching...", fg="#888888")
        if _root:
            _root.after(300, update_context_panel)

        # --- Exit cleanup for old scene (Step 9) ---
        if old_scene == 2:
            # Reset any active isolation bulbs before leaving Scene 2
            if receiver1.assigned_bulb:
                scene2_reset_bulb("R1 (Copper)")
            if receiver2.assigned_bulb:
                scene2_reset_bulb("R2 (White)")
            receiver1.is_isolated = False
            receiver2.is_isolated = False
            print("  Scene 2 exit: isolation cleared")

        # --- Entry setup for new scene ---
        if scene_num == 0:
            global scene0_state
            scene0_state = Scene0State()
            print("  Scene 0 state reset")
        elif scene_num == 1:
            global last_state_scene1
            last_state_scene1 = None
            print("  Scene 1 state reset")
        elif scene_num == 2:
            # Reset all lights to warm white on entry (clears previous scene colour)
            threading.Thread(
                target=lambda: run_hue_command(
                    ["openhue", "set", "room", HUE_ROOM_ID, "--on", "-t", "500", "--transition-time", "2s"],
                    "Scene 2 entry → warm white"
                ), daemon=True
            ).start()
            for s in bulb_display_state: s.update({"color": "warm_white", "on": True})
            log_event("Scene 2: all lights → warm white", "light")
            # Reset debounce timers so first proximity event triggers immediately
            receiver1.last_state_change_time = 0
            receiver2.last_state_change_time = 0
            receiver1_backup.last_state_change_time = 0
            receiver2_backup.last_state_change_time = 0
            print("  Scene 2 entry: lights → warm white")

    update_gui_status()

# Source toggle button references (updated in create_gui)
r1_source_btn = None
r2_source_btn = None
tx_source_btn = None

def _source_btn_style(is_backup):
    return {"bg": "#ff9944", "fg": "white"} if is_backup else {"bg": "#44bb44", "fg": "white"}

def toggle_r1_source():
    global r1_use_backup
    with backup_source_lock:
        r1_use_backup = not r1_use_backup
    label = "BACKUP" if r1_use_backup else "PRIMARY"
    if r1_source_btn:
        r1_source_btn.update(r1_use_backup)
    ts = time.strftime("%H:%M:%S")
    print(f"  [{ts}] Copper switched to {label}")
    log_event(f"Copper → {label}", "scene")

def toggle_r2_source():
    global r2_use_backup
    with backup_source_lock:
        r2_use_backup = not r2_use_backup
    label = "BACKUP" if r2_use_backup else "PRIMARY"
    if r2_source_btn:
        r2_source_btn.update(r2_use_backup)
    ts = time.strftime("%H:%M:%S")
    print(f"  [{ts}] White switched to {label}")
    log_event(f"White → {label}", "scene")

def toggle_tx_source():
    global tx_use_backup
    with backup_source_lock:
        tx_use_backup = not tx_use_backup
    label = "BACKUP" if tx_use_backup else "PRIMARY"
    if tx_source_btn:
        tx_source_btn.update(tx_use_backup)
    ts = time.strftime("%H:%M:%S")
    print(f"  [{ts}] Purple switched to {label}")
    log_event(f"Purple → {label}", "scene")

def toggle_all_sources():
    global r1_use_backup, r2_use_backup, tx_use_backup
    # Swap all to the same target: if any are primary, swap all to backup; else swap all to primary
    with backup_source_lock:
        target = not (r1_use_backup and r2_use_backup and tx_use_backup)
        r1_use_backup = target
        r2_use_backup = target
        tx_use_backup = target
    if r1_source_btn:
        r1_source_btn.update(target)
    if r2_source_btn:
        r2_source_btn.update(target)
    if tx_source_btn:
        tx_source_btn.update(target)
    label = "BACKUP" if target else "PRIMARY"
    ts = time.strftime("%H:%M:%S")
    print(f"  [{ts}] ALL rockers switched to {label}")
    log_event(f"All rockers → {label}", "scene")

def _update_scene_buttons(active):
    """Highlight the active scene button; dim the others"""
    for s, btn in scene_btns.items():
        if s == active:
            btn.config(relief="solid", bd=3, bg=SCENE_COLORS[s])
        else:
            btn.config(relief="flat", bd=1, bg=SCENE_DIM[s])


def update_context_panel():
    """Update the scene context label with current state in plain English"""
    if context_label is None:
        return
    with scene_lock:
        scene = current_scene

    if scene == 0:
        state = scene0_state.r1_is_close
        if state is None:
            text, color = "Waiting for R1 signal...", "#888888"
        elif state:
            text, color = "R1 Copper CLOSE · Warm white", "#ffcc88"
        else:
            text, color = "R1 Copper FAR · Cool white", "#ccdeff"
    elif scene == 1:
        r1, r2 = get_r1(), get_r2()
        dist_str = f"  ({r1.distance:.2f}m / {r2.distance:.2f}m)"
        state_map = {
            "both_close": ("BOTH CLOSE → Warm white", "#ffcc88"),
            "r1_far":     ("R1 FAR → Blue",           "#4499ff"),
            "r2_far":     ("R2 FAR → Cool white",     "#ccdeff"),
            "both_far":   ("BOTH FAR → Red",          "#ff4444"),
        }
        if last_state_scene1 in state_map:
            text, color = state_map[last_state_scene1]
            text += dist_str
        else:
            text = "Waiting for proximity data..." + dist_str
            color = "#888888"
    elif scene == 2:
        r1, r2 = get_r1(), get_r2()
        r1_str = "R1: ISOLATED" if r1.is_isolated else "R1: free"
        if r1.assigned_bulb:
            r1_str += f" · {r1.assigned_bulb['name']}"
        r2_str = "R2: ISOLATED" if r2.is_isolated else "R2: free"
        if r2.assigned_bulb:
            r2_str += f" · {r2.assigned_bulb['name']}"
        text = f"{r1_str}    {r2_str}"
        color = "#cc66ff"
    else:
        text, color = "", "#888888"

    context_label.config(text=text, fg=color)


class _ToggleSwitch:
    """Canvas-based pill toggle: green/knob-right = PRIMARY, orange/knob-left = BACKUP."""
    W, H, MARGIN, KNOB_PAD = 96, 32, 2, 4

    def __init__(self, parent, command):
        self._cmd = command
        self._is_backup = False
        bg = parent.cget("bg")
        self._cv = tk.Canvas(parent, width=self.W, height=self.H,
                             bg=bg, highlightthickness=0, cursor="hand2")
        self._cv.bind("<Button-1>", lambda e: self._cmd())
        self._draw()

    def pack(self, **kw):
        self._cv.pack(**kw)

    def update(self, is_backup):
        self._is_backup = is_backup
        self._draw()

    def _draw(self):
        cv = self._cv
        cv.delete("all")
        W, H, M, KP = self.W, self.H, self.MARGIN, self.KNOB_PAD
        # Pill inset by MARGIN on all sides to prevent clipping
        px0, py0, px1, py1 = M, M, W - M, H - M
        ph = py1 - py0          # pill height
        pr = ph // 2            # pill end-cap radius
        color = "#ff9944" if self._is_backup else "#44bb44"
        # Left semicircle (style=CHORD fills the arc region)
        cv.create_arc(px0, py0, px0 + ph, py1,
                      start=90, extent=180, fill=color, outline=color, style=tk.CHORD)
        # Right semicircle
        cv.create_arc(px1 - ph, py0, px1, py1,
                      start=270, extent=180, fill=color, outline=color, style=tk.CHORD)
        # Body rectangle bridging the two caps
        cv.create_rectangle(px0 + pr, py0, px1 - pr, py1, fill=color, outline=color)
        # Knob
        knob_d = ph - 2 * KP
        if not self._is_backup:
            kx1 = px1 - KP - knob_d   # right side
        else:
            kx1 = px0 + KP            # left side
        kx2 = kx1 + knob_d
        cv.create_oval(kx1, py0 + KP, kx2, py1 - KP, fill="white", outline="")
        # Label centred on pill
        label = "BACKUP" if self._is_backup else "PRIMARY"
        cy = (py0 + py1) // 2
        cv.create_text(W // 2, cy, text=label, fill="white", font=("Arial", 8, "bold"))


# ===== PHASE 5 — PUSHER BROADCAST =====

def build_state_payload():
    """Build the JSON-serialisable state dict sent to Pusher at ~5Hz."""
    r1 = get_r1(); r2 = get_r2(); tx = get_tx()
    with scene_lock:
        scene = current_scene
    now = time.time()
    conn = {k: (now - v) < CONNECTION_TIMEOUT for k, v in last_seen.items()}
    return {
        "scene": scene,
        "r1_distance": round(r1.distance, 3),
        "r2_distance": round(r2.distance, 3),
        "r1_isolated": r1.is_isolated,
        "r2_isolated": r2.is_isolated,
        "r1_accel": [round(r1.accel_x, 3), round(r1.accel_y, 3), round(r1.accel_z, 3)],
        "r2_accel": [round(r2.accel_x, 3), round(r2.accel_y, 3), round(r2.accel_z, 3)],
        "tx_accel": [round(tx.accel_x, 3), round(tx.accel_y, 3), round(tx.accel_z, 3)],
        "r1_gyro":  [round(r1.gyro_x, 3), round(r1.gyro_y, 3), round(r1.gyro_z, 3)],
        "r2_gyro":  [round(r2.gyro_x, 3), round(r2.gyro_y, 3), round(r2.gyro_z, 3)],
        "tx_gyro":  [round(tx.gyro_x, 3), round(tx.gyro_y, 3), round(tx.gyro_z, 3)],
        "hue_bulbs": [b["color"] for b in bulb_display_state],
        "r1_source": "backup" if r1_use_backup else "primary",
        "r2_source": "backup" if r2_use_backup else "primary",
        "tx_source": "backup" if tx_use_backup else "primary",
        "r1_live": conn.get("r1", False),
        "r2_live": conn.get("r2", False),
        "tx_live": conn.get("tx", False),
        "close_threshold": CLOSE_THRESHOLD,
        "far_threshold": FAR_THRESHOLD,
        "r1_session_active": _activity_r1.session_active,
        "r2_session_active": _activity_r2.session_active,
        "tx_session_active": _activity_tx.session_active,
        "r1_session_duration": round(_activity_r1.current_duration(), 1),
        "r2_session_duration": round(_activity_r2.current_duration(), 1),
        "tx_session_duration": round(_activity_tx.current_duration(), 1),
        "r1_wobble_ema": round(_activity_r1.ema, 3),
        "r2_wobble_ema": round(_activity_r2.ema, 3),
        "tx_wobble_ema": round(_activity_tx.ema, 3),
    }

def broadcast_trigger(trigger_type, **context):
    """Fire a one-shot 'trigger' event immediately (called on significant state changes)."""
    if _pusher_client:
        try:
            _pusher_client.trigger(PUSHER_CHANNEL, "trigger", {"type": trigger_type, **context})
        except Exception as e:
            print(f"[Pusher] trigger error: {e}")
    if WS_ENABLED:
        _ws_broadcast_sync({"event": "trigger", "type": trigger_type, **context})

def _pusher_broadcast_loop():
    """Background thread: send 'state' event to Pusher + WS at PUSHER_BROADCAST_HZ."""
    interval = 1.0 / max(1, PUSHER_BROADCAST_HZ)
    while True:
        payload = build_state_payload()
        if _pusher_client:
            try:
                _pusher_client.trigger(PUSHER_CHANNEL, "state", payload)
            except Exception as e:
                print(f"[Pusher] broadcast error: {e}")
        if WS_ENABLED:
            _ws_broadcast_sync({"event": "state", **payload})
        time.sleep(interval)


# ===== PHASE 5b — WEBSOCKET BROADCAST =====

async def _ws_handler(websocket):
    _ws_clients.add(websocket)
    try:
        await websocket.wait_closed()
    finally:
        _ws_clients.discard(websocket)

async def _ws_broadcast(msg: str):
    if _ws_clients:
        await asyncio.gather(
            *[c.send(msg) for c in set(_ws_clients)],
            return_exceptions=True
        )

def _ws_broadcast_sync(data: dict):
    if _ws_loop and _ws_loop.is_running():
        asyncio.run_coroutine_threadsafe(
            _ws_broadcast(json.dumps(data)), _ws_loop
        )

def _ws_server_thread():
    global _ws_loop
    import websockets
    _ws_loop = asyncio.new_event_loop()
    asyncio.set_event_loop(_ws_loop)
    async def _run():
        async with websockets.serve(_ws_handler, "0.0.0.0", WS_PORT):
            print(f"[WS] Server listening on ws://0.0.0.0:{WS_PORT}")
            await asyncio.Future()
    _ws_loop.run_until_complete(_run())


# ===== SUPABASE HELPERS =====

def _supabase_insert_async(table, data):
    """Fire-and-forget Supabase INSERT in a daemon thread."""
    if not _supabase_client:
        return
    def _do():
        try:
            _supabase_client.table(table).insert(data).execute()
        except Exception as e:
            print(f"[Supabase] {table} insert error: {e}")
    threading.Thread(target=_do, daemon=True).start()

def _supabase_update_async(table, match_col, match_val, data):
    """Fire-and-forget Supabase UPDATE … WHERE match_col = match_val."""
    if not _supabase_client:
        return
    def _do():
        try:
            _supabase_client.table(table).update(data).eq(match_col, match_val).execute()
        except Exception as e:
            print(f"[Supabase] {table} update error: {e}")
    threading.Thread(target=_do, daemon=True).start()

def _supabase_snapshot_loop():
    """Daemon thread: insert an activity snapshot every 30s."""
    while True:
        time.sleep(30)
        if not _supabase_client:
            continue
        try:
            now = time.time()
            with scene_lock:
                scene = current_scene
            r1 = get_r1(); r2 = get_r2()
            conn = {k: (now - v) < CONNECTION_TIMEOUT for k, v in last_seen.items()}
            _supabase_client.table("activity_snapshots").insert({
                "scene": scene,
                "r1_ema": round(_activity_r1.ema, 3),
                "r2_ema": round(_activity_r2.ema, 3),
                "tx_ema": round(_activity_tx.ema, 3),
                "r1_session_active": _activity_r1.session_active,
                "r2_session_active": _activity_r2.session_active,
                "tx_session_active": _activity_tx.session_active,
                "r1_session_duration_s": round(_activity_r1.current_duration(), 1),
                "r2_session_duration_s": round(_activity_r2.current_duration(), 1),
                "tx_session_duration_s": round(_activity_tx.current_duration(), 1),
                "r1_distance": round(r1.distance, 3),
                "r2_distance": round(r2.distance, 3),
                "r1_live": conn.get("r1", False),
                "r2_live": conn.get("r2", False),
                "tx_live": conn.get("tx", False),
            }).execute()
        except Exception as e:
            print(f"[Supabase] snapshot error: {e}")


def _build_dashboard(parent):
    """Build the live dashboard LabelFrame and populate _dash with widget refs"""
    global _dash

    bg = parent.cget("bg")

    dash_frame = tk.LabelFrame(parent, text="Dashboard", padx=8, pady=6,
                               font=("Arial", 10, "bold"))

    # --- Step 1: Connection status dots ---
    conn_row = tk.Frame(dash_frame)
    conn_row.pack(fill="x", pady=(0, 4))
    tk.Label(conn_row, text="Signal:", font=("Arial", 9, "bold"), width=7, anchor="w").pack(side="left")
    _dash["conn_dots"] = {}
    for key, label_text, label_color in [
        ("r1", "Copper", "#D2691E"),
        ("r2", "White",  "#888888"),
        ("tx", "Purple", "#9b6dff"),
    ]:
        col = tk.Frame(conn_row, bg=bg)
        col.pack(side="left", padx=8)
        cv = tk.Canvas(col, width=14, height=14, bg=bg, highlightthickness=0)
        cv.pack()
        dot = cv.create_oval(2, 2, 12, 12, fill="#444444", outline="")
        tk.Label(col, text=label_text, font=("Arial", 8), fg=label_color, bg=bg).pack()
        _dash["conn_dots"][key] = (cv, dot)

    # --- Step 2: Distance gauges (R1 and R2) ---
    _dash["gauges"] = {}
    GAUGE_W = 200
    GAUGE_MAX = 3.0
    for key, label_text, label_color in [
        ("r1", "Copper", "#D2691E"),
        ("r2", "White",  "#888888"),
    ]:
        row = tk.Frame(dash_frame)
        row.pack(fill="x", pady=1)
        tk.Label(row, text=label_text, font=("Arial", 9, "bold"), fg=label_color,
                 width=7, anchor="w").pack(side="left")
        cv = tk.Canvas(row, width=GAUGE_W, height=14, bg="#222222",
                       highlightthickness=1, highlightbackground="#555555")
        cv.pack(side="left", padx=4)
        bar = cv.create_rectangle(0, 0, 0, 14, fill="#44ff44", outline="")
        # Threshold markers: 0.8m and 2.0m
        for thresh in (0.8, 2.0):
            tx_px = int(thresh / GAUGE_MAX * GAUGE_W)
            cv.create_line(tx_px, 0, tx_px, 14, fill="#ffffff", width=1, dash=(2, 2))
        dist_lbl = tk.Label(row, text="--m", font=("Arial", 9), width=6, anchor="w")
        dist_lbl.pack(side="left")
        _dash["gauges"][key] = (cv, bar, dist_lbl)

    # --- Step 3: Hue bulb state circles ---
    bulb_row = tk.Frame(dash_frame)
    bulb_row.pack(fill="x", pady=(2, 4))
    tk.Label(bulb_row, text="Hue:", font=("Arial", 9, "bold"), width=7, anchor="w").pack(side="left")
    _dash["bulbs"] = []
    short_names = ["Lamp 1", "Lamp 2", "Light 3", "Lamp 4"]
    for i in range(len(HUE_LIGHTS)):
        col = tk.Frame(bulb_row, bg=bg)
        col.pack(side="left", padx=5)
        cv = tk.Canvas(col, width=28, height=28, bg=bg, highlightthickness=0)
        cv.pack()
        dot = cv.create_oval(2, 2, 26, 26, fill="#ffcc88", outline="#666666", width=1)
        tk.Label(col, text=short_names[i], font=("Arial", 7), bg=bg).pack()
        _dash["bulbs"].append((cv, dot))

    # --- Step 4: OSC activity dots ---
    osc_row = tk.Frame(dash_frame)
    osc_row.pack(fill="x", pady=(0, 2))
    tk.Label(osc_row, text="OSC:", font=("Arial", 9, "bold"), width=7, anchor="w").pack(side="left")
    _dash["osc_dots"] = {}
    PORT_LABELS = [
        (R1_PROXIMITY_PORT, "R1 prx"),
        (R1_SENSOR_PORT,    "R1 sen"),
        (R2_PROXIMITY_PORT, "R2 prx"),
        (R2_SENSOR_PORT,    "R2 sen"),
        (TRANSMITTER_PORT,  "TX"),
        (VCV_RACK_PORT,     "→VCV"),
    ]
    for port, label_text in PORT_LABELS:
        col = tk.Frame(osc_row, bg=bg)
        col.pack(side="left", padx=3)
        cv = tk.Canvas(col, width=10, height=10, bg=bg, highlightthickness=0)
        cv.pack()
        dot = cv.create_oval(1, 1, 9, 9, fill="#333333", outline="")
        tk.Label(col, text=label_text, font=("Arial", 7), bg=bg).pack()
        _dash["osc_dots"][port] = (cv, dot)

    return dash_frame


def update_dashboard(root):
    """Refresh all dashboard widgets; reschedules itself every 100ms"""
    now = time.time()

    # Step 1: Connection dots
    for key, (cv, dot) in _dash.get("conn_dots", {}).items():
        live = (now - last_seen.get(key, 0.0)) < CONNECTION_TIMEOUT
        cv.itemconfig(dot, fill="#44ff44" if live else "#444444")

    # Step 2: Distance gauges
    rocker_getters = {"r1": get_r1, "r2": get_r2}
    for key, (cv, bar, lbl) in _dash.get("gauges", {}).items():
        d = rocker_getters[key]().distance
        clamped = max(0.0, min(d, 3.0))
        bar_w = int(clamped / 3.0 * 200)
        fill = "#44ff44" if d <= 0.65 else ("#ffee44" if d <= 0.95 else "#ff4444")
        cv.coords(bar, 0, 0, bar_w, 14)
        cv.itemconfig(bar, fill=fill)
        lbl.config(text=f"{d:.2f}m")

    # Step 3: Hue bulb circles
    for i, (cv, dot) in enumerate(_dash.get("bulbs", [])):
        if i < len(bulb_display_state):
            state = bulb_display_state[i]
            hex_color = _color_to_hex(state["color"]) if state["on"] else "#333333"
            cv.itemconfig(dot, fill=hex_color)

    # Step 4: OSC activity dots
    for port, (cv, dot) in _dash.get("osc_dots", {}).items():
        active = (now - last_osc_time.get(port, 0.0)) < OSC_ACTIVITY_WINDOW
        cv.itemconfig(dot, fill="#ffee44" if active else "#333333")

    # Step 10: Timeout detection + logging
    global _timeout_logged, _all_timeout_triggered
    _ROCKER_NAMES = {"r1": "R1 Copper", "r2": "R2 White", "tx": "TX Purple"}
    all_offline = True
    for key, display_name in _ROCKER_NAMES.items():
        live = (now - last_seen.get(key, 0.0)) < CONNECTION_TIMEOUT
        if live:
            all_offline = False
            if _timeout_logged[key]:
                _timeout_logged[key] = False
                log_event(f"{display_name} reconnected", "scene")
        else:
            if not _timeout_logged[key]:
                _timeout_logged[key] = True
                log_event(f"{display_name} TIMEOUT", "proximity")

    if all_offline and not _all_timeout_triggered and any(last_seen.values()):
        _all_timeout_triggered = True
        threading.Thread(
            target=lambda: run_hue_command(
                ["openhue", "set", "room", HUE_ROOM_ID, "--on", "-t", "500", "--transition-time", "3s"],
                "All timeout → warm white"
            ), daemon=True
        ).start()
        for s in bulb_display_state: s.update({"color": "warm_white", "on": True})
        log_event("ALL OFFLINE → warm white", "proximity")
    elif not all_offline:
        _all_timeout_triggered = False

    # Activity timeout fallback: end sessions for offline rockers
    for _akey, _adet in [("r1", _activity_r1), ("r2", _activity_r2), ("tx", _activity_tx)]:
        if _timeout_logged.get(_akey):
            _aevt = _adet.check_timeout()
            if _aevt:
                _on_activity_event(_adet, _aevt)

    root.after(100, lambda: update_dashboard(root))


def create_gui():
    """Create the GUI window"""
    global status_label, r1_label, r2_label, r1_source_btn, r2_source_btn, tx_source_btn
    global context_label, event_log, _root

    root = tk.Tk()
    root.title("Wobble Unified Processor")
    root.geometry("540x800")

    # Title
    title_label = tk.Label(root, text="Wobble Unified Processor", font=("Arial", 18, "bold"))
    title_label.pack(pady=8)

    # ===== WOBBLE SOURCES =====
    sources_frame = tk.LabelFrame(root, text="Wobble Sources", padx=8, pady=6, font=("Arial", 10, "bold"))
    sources_frame.pack(fill="x", padx=10, pady=(0, 4))

    def _make_source_row(parent, label_text, label_bg, label_fg, toggle_cmd):
        row = tk.Frame(parent)
        row.pack(fill="x", pady=1)
        tk.Label(row, text=label_text, font=("Arial", 10, "bold"), bg=label_bg, fg=label_fg,
                 width=10, anchor="w", padx=4).pack(side="left")
        sw = _ToggleSwitch(row, toggle_cmd)
        sw.pack(side="left", padx=6)
        return sw

    r1_source_btn = _make_source_row(sources_frame, "Copper", "#D2691E", "white", toggle_r1_source)
    r2_source_btn = _make_source_row(sources_frame, "White", "#888888", "white", toggle_r2_source)
    tx_source_btn = _make_source_row(sources_frame, "Purple", "#9b6dff", "white", toggle_tx_source)

    _swap_f = tk.Frame(sources_frame, bg="#222222", cursor="hand2")
    _swap_l = tk.Label(_swap_f, text="Swap All", bg="#222222", fg="white",
                       font=("Arial", 9, "bold"), cursor="hand2", padx=16, pady=4)
    _swap_l.pack()
    _swap_f.bind("<Button-1>", lambda e: toggle_all_sources())
    _swap_l.bind("<Button-1>", lambda e: toggle_all_sources())
    _swap_f.pack(pady=(4, 2))

    # ===== DASHBOARD =====
    dashboard_frame = _build_dashboard(root)
    dashboard_frame.pack(fill="x", padx=10, pady=(0, 4))

    # Start dashboard polling
    root.after(100, lambda: update_dashboard(root))

    # ===== SCENE SELECTION BUTTONS =====
    button_frame = tk.Frame(root)
    button_frame.pack(pady=(4, 2))

    scene0_btn = tk.Button(
        button_frame, text="Scene 0\nIndividual Layers",
        command=lambda: switch_to_scene(0),
        width=15, height=3, font=("Arial", 10, "bold"),
        bg=SCENE_COLORS[0], relief="solid", bd=3,   # scene 0 active on startup
    )
    scene0_btn.grid(row=0, column=0, padx=5)

    scene1_btn = tk.Button(
        button_frame, text="Scene 1\nDistance States",
        command=lambda: switch_to_scene(1),
        width=15, height=3, font=("Arial", 10, "bold"),
        bg=SCENE_DIM[1], relief="flat", bd=1,
    )
    scene1_btn.grid(row=0, column=1, padx=5)

    scene2_btn = tk.Button(
        button_frame, text="Scene 2\nIsolation Mode",
        command=lambda: switch_to_scene(2),
        width=15, height=3, font=("Arial", 10, "bold"),
        bg=SCENE_DIM[2], relief="flat", bd=1,
    )
    scene2_btn.grid(row=0, column=2, padx=5)

    scene_btns[0] = scene0_btn
    scene_btns[1] = scene1_btn
    scene_btns[2] = scene2_btn

    # ===== SCENE CONTEXT PANEL =====
    ctx_frame = tk.LabelFrame(root, text="Scene State", padx=8, pady=4,
                              font=("Arial", 9, "bold"))
    ctx_frame.pack(fill="x", padx=10, pady=(4, 2))
    context_label = tk.Label(ctx_frame, text="Waiting for R1 signal...",
                             font=("Arial", 10), fg="#888888", anchor="w", justify="left")
    context_label.pack(fill="x")

    # ===== EVENT LOG =====
    log_frame = tk.LabelFrame(root, text="Event Log", padx=6, pady=4,
                              font=("Arial", 9, "bold"))
    log_frame.pack(fill="both", expand=True, padx=10, pady=(2, 8))

    event_log = tk.Text(log_frame, height=8, state=tk.DISABLED, font=("Courier", 9),
                        bg="#1a1a1a", fg="#cccccc", wrap="none",
                        relief="flat", bd=0)
    event_log.pack(fill="both", expand=True)

    # Color tags
    event_log.tag_config("light",     foreground="#f0c040")
    event_log.tag_config("scene",     foreground="#9b6dff")
    event_log.tag_config("proximity", foreground="#4a9edd")
    event_log.tag_config("info",      foreground="#cccccc")

    # ===== SETTINGS (collapsible, Step 8) =====
    settings_frame = tk.LabelFrame(root, text="Settings", padx=8, pady=4,
                                   font=("Arial", 9, "bold"))
    settings_inner = tk.Frame(settings_frame)

    def _make_slider_row(parent, label, from_, to_, resolution, get_val, cmd, unit="m"):
        row = tk.Frame(parent)
        row.pack(fill="x", pady=1)
        tk.Label(row, text=label, font=("Arial", 9), width=18, anchor="w").pack(side="left")
        fmt = "{:.0f}" if resolution >= 1 else "{:.2f}"
        def _fmt(v):
            return fmt.format(float(v)) + unit
        val_lbl = tk.Label(row, text=_fmt(get_val()), font=("Arial", 9), width=6, anchor="w")
        def _on_slide(v):
            cmd(v)
            val_lbl.config(text=_fmt(v))
        sl = tk.Scale(row, from_=from_, to=to_, resolution=resolution,
                      orient="horizontal", length=160, showvalue=False,
                      command=_on_slide)
        sl.set(get_val())
        sl.pack(side="left", padx=4)
        val_lbl.pack(side="left")
        return sl

    _make_slider_row(settings_inner, "Close threshold",
                     0.3, 2.0, 0.05, lambda: CLOSE_THRESHOLD, _set_close_threshold)
    _make_slider_row(settings_inner, "Far threshold",
                     0.5, 3.0, 0.05, lambda: FAR_THRESHOLD,   _set_far_threshold)
    _make_slider_row(settings_inner, "Hysteresis",
                     0.05, 0.4, 0.01, lambda: HYSTERESIS,     _set_hysteresis)

    # Activity detection sliders
    tk.Label(settings_inner, text="Activity Detection", font=("Arial", 9, "bold"),
             anchor="w").pack(fill="x", pady=(6, 2))
    _make_slider_row(settings_inner, "Wobble active thresh",
                     0.2, 2.0, 0.05, lambda: WOBBLE_ACTIVE_THRESHOLD, _set_wobble_active, unit="")
    _make_slider_row(settings_inner, "Wobble idle thresh",
                     0.05, 1.0, 0.05, lambda: WOBBLE_IDLE_THRESHOLD,  _set_wobble_idle, unit="")
    _make_slider_row(settings_inner, "Session timeout",
                     10, 180, 5, lambda: SESSION_TIMEOUT_S,            _set_session_timeout, unit="s")

    _save_f = tk.Frame(settings_inner, bg="#0a6600", cursor="hand2")
    _save_l = tk.Label(_save_f, text="Save to config.json", bg="#0a6600", fg="white",
                       font=("Arial", 9), cursor="hand2", padx=12, pady=4)
    _save_l.pack()
    _save_f.bind("<Button-1>", lambda e: _save_config())
    _save_l.bind("<Button-1>", lambda e: _save_config())
    _save_f.pack(pady=(4, 2))

    _settings_open = [False]

    def _toggle_settings():
        if _settings_open[0]:
            settings_inner.pack_forget()
            settings_frame.config(text="Settings ▶")
            _settings_open[0] = False
        else:
            settings_inner.pack(fill="x")
            settings_frame.config(text="Settings ▼")
            _settings_open[0] = True

    settings_frame.config(text="Settings ▶")
    settings_frame.bind("<Button-1>", lambda e: _toggle_settings())
    tk.Button(settings_frame, text="▶ expand", font=("Arial", 8), relief="flat",
              command=_toggle_settings, bg=root.cget("bg"), fg="#888888",
              cursor="hand2").pack(anchor="w")
    settings_frame.pack(fill="x", padx=10, pady=(0, 6))

    root.bind("1", lambda e: switch_to_scene(0))
    root.bind("2", lambda e: switch_to_scene(1))
    root.bind("3", lambda e: switch_to_scene(2))

    global _root
    _root = root
    return root

# ===== TERMINAL MOVEMENT MONITOR =====
def create_bar(value, min_val, max_val, width=40):
    """Create a visual bar representation of a value between min and max"""
    if max_val == min_val:
        normalized = 0.5
    else:
        normalized = (value - min_val) / (max_val - min_val)
    
    bar_length = int(normalized * width)
    bar = "█" * bar_length + "░" * (width - bar_length)
    return bar

def display_movement_monitor():
    """Continuously display movement data in terminal"""
    while movement_monitor.display_enabled:
        try:
            # Clear screen (works on macOS/Linux)
            os.system('clear')
            
            with movement_monitor.lock:
                # Header
                print("=" * 120)
                print("WOBBLE MOVEMENT MONITOR - Real-time Sensor Data with Min/Max Tracking")
                print("=" * 120)
                print("Press Ctrl+C in terminal to reset min/max values\n")
                
                # R1 - Copper Rocker
                print("┌─── RECEIVER 1 (COPPER) " + "─" * 94 + "┐")
                print("│ ACCELEROMETER (m/s²)")
                print(f"│  X: {receiver1.accel_x:7.2f} [{movement_monitor.r1_accel_x_min:7.2f} to {movement_monitor.r1_accel_x_max:7.2f}]  {create_bar(receiver1.accel_x, movement_monitor.r1_accel_x_min, movement_monitor.r1_accel_x_max)}")
                print(f"│  Y: {receiver1.accel_y:7.2f} [{movement_monitor.r1_accel_y_min:7.2f} to {movement_monitor.r1_accel_y_max:7.2f}]  {create_bar(receiver1.accel_y, movement_monitor.r1_accel_y_min, movement_monitor.r1_accel_y_max)}")
                print(f"│  Z: {receiver1.accel_z:7.2f} [{movement_monitor.r1_accel_z_min:7.2f} to {movement_monitor.r1_accel_z_max:7.2f}]  {create_bar(receiver1.accel_z, movement_monitor.r1_accel_z_min, movement_monitor.r1_accel_z_max)}")
                print("│")
                print("│ GYROSCOPE (rad/s)")
                print(f"│  X: {receiver1.gyro_x:7.2f} [{movement_monitor.r1_gyro_x_min:7.2f} to {movement_monitor.r1_gyro_x_max:7.2f}]  {create_bar(receiver1.gyro_x, movement_monitor.r1_gyro_x_min, movement_monitor.r1_gyro_x_max)}")
                print(f"│  Y: {receiver1.gyro_y:7.2f} [{movement_monitor.r1_gyro_y_min:7.2f} to {movement_monitor.r1_gyro_y_max:7.2f}]  {create_bar(receiver1.gyro_y, movement_monitor.r1_gyro_y_min, movement_monitor.r1_gyro_y_max)}")
                print(f"│  Z: {receiver1.gyro_z:7.2f} [{movement_monitor.r1_gyro_z_min:7.2f} to {movement_monitor.r1_gyro_z_max:7.2f}]  {create_bar(receiver1.gyro_z, movement_monitor.r1_gyro_z_min, movement_monitor.r1_gyro_z_max)}")
                print("└" + "─" * 118 + "┘\n")
                
                # R2 - White Rocker
                print("┌─── RECEIVER 2 (WHITE) " + "─" * 95 + "┐")
                print("│ ACCELEROMETER (m/s²)")
                print(f"│  X: {receiver2.accel_x:7.2f} [{movement_monitor.r2_accel_x_min:7.2f} to {movement_monitor.r2_accel_x_max:7.2f}]  {create_bar(receiver2.accel_x, movement_monitor.r2_accel_x_min, movement_monitor.r2_accel_x_max)}")
                print(f"│  Y: {receiver2.accel_y:7.2f} [{movement_monitor.r2_accel_y_min:7.2f} to {movement_monitor.r2_accel_y_max:7.2f}]  {create_bar(receiver2.accel_y, movement_monitor.r2_accel_y_min, movement_monitor.r2_accel_y_max)}")
                print(f"│  Z: {receiver2.accel_z:7.2f} [{movement_monitor.r2_accel_z_min:7.2f} to {movement_monitor.r2_accel_z_max:7.2f}]  {create_bar(receiver2.accel_z, movement_monitor.r2_accel_z_min, movement_monitor.r2_accel_z_max)}")
                print("│")
                print("│ GYROSCOPE (rad/s)")
                print(f"│  X: {receiver2.gyro_x:7.2f} [{movement_monitor.r2_gyro_x_min:7.2f} to {movement_monitor.r2_gyro_x_max:7.2f}]  {create_bar(receiver2.gyro_x, movement_monitor.r2_gyro_x_min, movement_monitor.r2_gyro_x_max)}")
                print(f"│  Y: {receiver2.gyro_y:7.2f} [{movement_monitor.r2_gyro_y_min:7.2f} to {movement_monitor.r2_gyro_y_max:7.2f}]  {create_bar(receiver2.gyro_y, movement_monitor.r2_gyro_y_min, movement_monitor.r2_gyro_y_max)}")
                print(f"│  Z: {receiver2.gyro_z:7.2f} [{movement_monitor.r2_gyro_z_min:7.2f} to {movement_monitor.r2_gyro_z_max:7.2f}]  {create_bar(receiver2.gyro_z, movement_monitor.r2_gyro_z_min, movement_monitor.r2_gyro_z_max)}")
                print("└" + "─" * 118 + "┘\n")
                
                # Transmitter - Purple
                print("┌─── TRANSMITTER (PURPLE) " + "─" * 93 + "┐")
                print("│ ACCELEROMETER (m/s²)")
                print(f"│  X: {transmitter.accel_x:7.2f} [{movement_monitor.tx_accel_x_min:7.2f} to {movement_monitor.tx_accel_x_max:7.2f}]  {create_bar(transmitter.accel_x, movement_monitor.tx_accel_x_min, movement_monitor.tx_accel_x_max)}")
                print(f"│  Y: {transmitter.accel_y:7.2f} [{movement_monitor.tx_accel_y_min:7.2f} to {movement_monitor.tx_accel_y_max:7.2f}]  {create_bar(transmitter.accel_y, movement_monitor.tx_accel_y_min, movement_monitor.tx_accel_y_max)}")
                print(f"│  Z: {transmitter.accel_z:7.2f} [{movement_monitor.tx_accel_z_min:7.2f} to {movement_monitor.tx_accel_z_max:7.2f}]  {create_bar(transmitter.accel_z, movement_monitor.tx_accel_z_min, movement_monitor.tx_accel_z_max)}")
                print("│")
                print("│ GYROSCOPE (rad/s)")
                print(f"│  X: {transmitter.gyro_x:7.2f} [{movement_monitor.tx_gyro_x_min:7.2f} to {movement_monitor.tx_gyro_x_max:7.2f}]  {create_bar(transmitter.gyro_x, movement_monitor.tx_gyro_x_min, movement_monitor.tx_gyro_x_max)}")
                print(f"│  Y: {transmitter.gyro_y:7.2f} [{movement_monitor.tx_gyro_y_min:7.2f} to {movement_monitor.tx_gyro_y_max:7.2f}]  {create_bar(transmitter.gyro_y, movement_monitor.tx_gyro_y_min, movement_monitor.tx_gyro_y_max)}")
                print(f"│  Z: {transmitter.gyro_z:7.2f} [{movement_monitor.tx_gyro_z_min:7.2f} to {movement_monitor.tx_gyro_z_max:7.2f}]  {create_bar(transmitter.gyro_z, movement_monitor.tx_gyro_z_min, movement_monitor.tx_gyro_z_max)}")
                print("└" + "─" * 118 + "┘\n")
                
                # Scene info
                with scene_lock:
                    scene = current_scene
                print(f"Current Scene: {scene} | Distance R1: {receiver1.distance:.2f}m | Distance R2: {receiver2.distance:.2f}m")
                print("\nPress 'r' + Enter in separate terminal to reset min/max tracking")
                
            time.sleep(0.1)  # Update 10 times per second
            
        except KeyboardInterrupt:
            print("\nResetting min/max values...")
            movement_monitor.reset()
            time.sleep(1)
        except Exception as e:
            print(f"Display error: {e}")
            time.sleep(1)

# ===== SERVER SETUP =====
def create_server(port, dispatcher_obj, name):
    """Create and run OSC server in separate thread"""
    server = osc_server.ThreadingOSCUDPServer(("0.0.0.0", port), dispatcher_obj)
    print(f"✓ {name} server listening on port {port}")
    server_thread = threading.Thread(target=server.serve_forever, daemon=True)
    server_thread.start()
    return server

def main():
    print("\n" + "="*60)
    print("Wobble Unified Processor")
    print("="*60 + "\n")

    # ===== PUSHER INIT (Phase 5) =====
    global _pusher_client
    if PUSHER_ENABLED:
        try:
            import pusher as _pusher_lib
            _pusher_client = _pusher_lib.Pusher(
                app_id=PUSHER_APP_ID, key=PUSHER_KEY,
                secret=PUSHER_SECRET, cluster=PUSHER_CLUSTER, ssl=True
            )
            threading.Thread(target=_pusher_broadcast_loop, daemon=True).start()
            print(f"[Pusher] Live dashboard active — broadcasting on '{PUSHER_CHANNEL}' at {PUSHER_BROADCAST_HZ}Hz")
            if VERCEL_URL:
                try:
                    import qrcode as _qr
                    qr = _qr.QRCode(border=1)
                    qr.add_data(VERCEL_URL)
                    qr.make(fit=True)
                    print(f"\n  Dashboard URL: {VERCEL_URL}")
                    qr.print_ascii(invert=True)
                except ImportError:
                    print(f"  Dashboard URL: {VERCEL_URL}  (pip install qrcode to show QR)")
        except ImportError:
            print("[Pusher] 'pusher' package not installed — run: pip install pusher")
        except Exception as e:
            print(f"[Pusher] init error: {e}")
    else:
        print("[Pusher] disabled — set PUSHER_ENABLED = True and fill credentials to activate")

    # ===== WEBSOCKET INIT (Phase 5b) =====
    if WS_ENABLED:
        try:
            import websockets as _ws_check  # noqa
            threading.Thread(target=_ws_server_thread, daemon=True).start()
            if VERCEL_URL:
                print(f"  Remote dashboard: {VERCEL_URL}")
                print(f"  Expose WS with:   cloudflared tunnel --url ws://localhost:{WS_PORT}")
        except ImportError:
            print("[WS] 'websockets' not installed — run: pip install websockets")

    # ===== SUPABASE INIT =====
    global _supabase_client
    if SUPABASE_URL and SUPABASE_KEY:
        try:
            from supabase import create_client
            _supabase_client = create_client(SUPABASE_URL, SUPABASE_KEY)
            threading.Thread(target=_supabase_snapshot_loop, daemon=True).start()
            print(f"[Supabase] Connected — snapshots every 30s")
        except ImportError:
            print("[Supabase] 'supabase' package not installed — run: pip install supabase")
        except Exception as e:
            print(f"[Supabase] init error: {e}")
    else:
        print("[Supabase] disabled — set SUPABASE_URL and SUPABASE_SERVICE_KEY in .env")

    print("Loading config...")
    _load_config()

    print("Configuration:")
    print(f"  Close Threshold: ≤{CLOSE_THRESHOLD}m")
    print(f"  Far Threshold: ≥{FAR_THRESHOLD}m")
    print(f"  Isolation Threshold: {ISOLATION_THRESHOLD}m ±{HYSTERESIS}m")
    print(f"  VCV Rack Output: port {VCV_RACK_PORT}\n")
    
    # Create dispatchers for each input port
    r1_proximity_disp = dispatcher.Dispatcher()
    r1_proximity_disp.map("/proximity/distance", r1_proximity_handler)
    
    r2_proximity_disp = dispatcher.Dispatcher()
    r2_proximity_disp.map("/proximity/distance", r2_proximity_handler)
    
    r1_sensor_disp = dispatcher.Dispatcher()
    r1_sensor_disp.map("/accel/x", r1_accel_x_handler)
    r1_sensor_disp.map("/accel/y", r1_accel_y_handler)
    r1_sensor_disp.map("/accel/z", r1_accel_z_handler)
    r1_sensor_disp.map("/gyro/x", r1_gyro_x_handler)
    r1_sensor_disp.map("/gyro/y", r1_gyro_y_handler)
    r1_sensor_disp.map("/gyro/z", r1_gyro_z_handler)
    
    r2_sensor_disp = dispatcher.Dispatcher()
    r2_sensor_disp.map("/accel/x", r2_accel_x_handler)
    r2_sensor_disp.map("/accel/y", r2_accel_y_handler)
    r2_sensor_disp.map("/accel/z", r2_accel_z_handler)
    r2_sensor_disp.map("/gyro/x", r2_gyro_x_handler)
    r2_sensor_disp.map("/gyro/y", r2_gyro_y_handler)
    r2_sensor_disp.map("/gyro/z", r2_gyro_z_handler)
    
    transmitter_disp = dispatcher.Dispatcher()
    transmitter_disp.map("/accel/x", transmitter_accel_x_handler)
    transmitter_disp.map("/accel/y", transmitter_accel_y_handler)
    transmitter_disp.map("/accel/z", transmitter_accel_z_handler)
    transmitter_disp.map("/gyro/x", transmitter_gyro_x_handler)
    transmitter_disp.map("/gyro/y", transmitter_gyro_y_handler)
    transmitter_disp.map("/gyro/z", transmitter_gyro_z_handler)
    
    # ===== BACKUP DISPATCHERS =====
    r1b_proximity_disp = dispatcher.Dispatcher()
    r1b_proximity_disp.map("/proximity/distance", r1b_proximity_handler)

    r2b_proximity_disp = dispatcher.Dispatcher()
    r2b_proximity_disp.map("/proximity/distance", r2b_proximity_handler)

    r1b_sensor_disp = dispatcher.Dispatcher()
    r1b_sensor_disp.map("/accel/x", r1b_accel_x_handler)
    r1b_sensor_disp.map("/accel/y", r1b_accel_y_handler)
    r1b_sensor_disp.map("/accel/z", r1b_accel_z_handler)
    r1b_sensor_disp.map("/gyro/x", r1b_gyro_x_handler)
    r1b_sensor_disp.map("/gyro/y", r1b_gyro_y_handler)
    r1b_sensor_disp.map("/gyro/z", r1b_gyro_z_handler)

    r2b_sensor_disp = dispatcher.Dispatcher()
    r2b_sensor_disp.map("/accel/x", r2b_accel_x_handler)
    r2b_sensor_disp.map("/accel/y", r2b_accel_y_handler)
    r2b_sensor_disp.map("/accel/z", r2b_accel_z_handler)
    r2b_sensor_disp.map("/gyro/x", r2b_gyro_x_handler)
    r2b_sensor_disp.map("/gyro/y", r2b_gyro_y_handler)
    r2b_sensor_disp.map("/gyro/z", r2b_gyro_z_handler)

    transmitter_b_disp = dispatcher.Dispatcher()
    transmitter_b_disp.map("/accel/x", txb_accel_x_handler)
    transmitter_b_disp.map("/accel/y", txb_accel_y_handler)
    transmitter_b_disp.map("/accel/z", txb_accel_z_handler)
    transmitter_b_disp.map("/gyro/x", txb_gyro_x_handler)
    transmitter_b_disp.map("/gyro/y", txb_gyro_y_handler)
    transmitter_b_disp.map("/gyro/z", txb_gyro_z_handler)

    # Start all input servers
    print("Starting OSC input servers (primary):")
    create_server(R1_PROXIMITY_PORT, r1_proximity_disp, "R1 Proximity")
    create_server(R2_PROXIMITY_PORT, r2_proximity_disp, "R2 Proximity")
    create_server(R1_SENSOR_PORT, r1_sensor_disp, "R1 Sensors")
    create_server(R2_SENSOR_PORT, r2_sensor_disp, "R2 Sensors")
    create_server(TRANSMITTER_PORT, transmitter_disp, "Transmitter")

    print("Starting OSC input servers (backup):")
    create_server(R1B_PROXIMITY_PORT, r1b_proximity_disp, "R1B Proximity")
    create_server(R2B_PROXIMITY_PORT, r2b_proximity_disp, "R2B Proximity")
    create_server(R1B_SENSOR_PORT, r1b_sensor_disp, "R1B Sensors")
    create_server(R2B_SENSOR_PORT, r2b_sensor_disp, "R2B Sensors")
    create_server(TRANSMITTER_B_PORT, transmitter_b_disp, "Transmitter B")
    
    print(f"\nOSC output to VCV Rack:")
    print(f"  All scenes: port {VCV_RACK_PORT} (addresses: /r1/*, /r2/*, /transmitter/*)")
    print("="*60 + "\n")
    
    # Initialize Scene 0 as active
    print("Initializing Scene 0 as active...")
    print("  Scene 0 initialized\n")
    
    # Start movement monitor in separate thread
    print("Starting terminal movement monitor...")
    monitor_thread = threading.Thread(target=display_movement_monitor, daemon=True)
    monitor_thread.start()
    
    print("Starting GUI...")
    
    # Create and run GUI
    root = create_gui()
    root.mainloop()
    
    # Cleanup
    movement_monitor.display_enabled = False

if __name__ == "__main__":
    main()
