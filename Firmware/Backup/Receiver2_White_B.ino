/*
 * Wobble Unified - Receiver 2 BACKUP (White Rocker B)
 * Adafruit QT Py ESP32-S3
 *
 * BACKUP BOARD — identical to Receiver2_White.ino except for port numbers.
 * Flash this onto the spare White board. Keep the primary board powered if
 * possible; Python listens on both ports simultaneously.
 *
 * This board:
 * - Scans for BLE beacon and detects proximity
 * - Sends proximity events to port 8102 (/proximity/distance)
 * - Sends LSM6DSOX sensor data to port 8106
 *
 * Compatible with all three scenes (Scene 0, Scene 1, Scene 2)
 * Python processor handles scene-specific logic
 */

// ===== WIFI & OSC CONFIGURATION =====
const char* ssid = "Dr.Wifi";
const char* password = "IthurtswhenIP1800";
const char* oscDestIP = "192.168.50.201";     // Your laptop IP

// OSC ports (BACKUP — 81xx)
const int oscProximityPort = 8102;  // Backup port for /proximity/distance messages
const int oscSensorPort = 8106;      // Backup port for LSM6DSOX sensor data
const int oscLocalPort = 9102;       // Local port for OSC

// ===== BLE INCLUDES =====
#include <BLEDevice.h>
#include <BLEUtils.h>
#include <BLEScan.h>
#include <BLEAdvertisedDevice.h>

// ===== WIFI & OSC INCLUDES =====
#include <WiFi.h>
#include <WiFiUdp.h>
#include <OSCMessage.h>
#include <OSCBundle.h>

// ===== SENSOR INCLUDES =====
#include <Adafruit_LSM6DSOX.h>
#include <Wire.h>

// ===== BLE CONFIGURATION =====
#define DEVICE_NAME "QTPy_ESP32_B" // Must match backup transmitter beacon name

// RSSI to distance calculation
#define MEASURED_POWER -90
#define PATH_LOSS_EXPONENT 2.0

// Proximity threshold
#define PROXIMITY_THRESHOLD 0.80
#define HYSTERESIS 0.05

// Smoothing parameters
#define SMOOTHING_WINDOW 5
#define OUTLIER_THRESHOLD 1.5

// ===== LSM6DSOX CONFIGURATION =====
#define SDA1_PIN 41
#define SCL1_PIN 40
#define SENSOR_UPDATE_INTERVAL 40  // 25Hz for sensor data

// ===== GLOBAL VARIABLES =====
BLEScan* pBLEScan;
WiFiUDP udp;
Adafruit_LSM6DSOX sox;

// Proximity tracking
bool isInProximity = false;
bool lastProximityState = false;
unsigned long lastStateChange = 0;
const unsigned long DEBOUNCE_TIME = 200;

// Distance smoothing
float distanceBuffer[SMOOTHING_WINDOW];
int bufferIndex = 0;
int bufferCount = 0;
float lastValidDistance = -1.0;

// Timing
unsigned long lastSensorSendTime = 0;
unsigned long lastPrintTime = 0;
const unsigned long PRINT_INTERVAL = 500;

// BLE scan control
TaskHandle_t BLETask;
volatile bool bleScanInProgress = false;

// ===== RSSI TO DISTANCE CONVERSION =====
float calculateDistance(int rssi) {
  if (rssi == 0) {
    return -1.0;
  }

  float ratio = (MEASURED_POWER - rssi) / (10.0 * PATH_LOSS_EXPONENT);
  float distance = pow(10, ratio);

  return distance;
}

// ===== DISTANCE SMOOTHING =====
float smoothDistance(float rawDistance) {
  if (rawDistance < 0) return lastValidDistance;

  if (lastValidDistance > 0 && abs(rawDistance - lastValidDistance) > OUTLIER_THRESHOLD) {
    return lastValidDistance;
  }

  distanceBuffer[bufferIndex] = rawDistance;
  bufferIndex = (bufferIndex + 1) % SMOOTHING_WINDOW;
  if (bufferCount < SMOOTHING_WINDOW) bufferCount++;

  float sum = 0;
  for (int i = 0; i < bufferCount; i++) {
    sum += distanceBuffer[i];
  }
  float smoothed = sum / bufferCount;

  lastValidDistance = smoothed;
  return smoothed;
}

// ===== OSC FUNCTIONS =====
void sendOSCProximity(float distance, bool inRange) {
  OSCMessage msg("/proximity/distance");
  msg.add(distance);
  msg.add((int32_t)(inRange ? 1 : 0));

  udp.beginPacket(oscDestIP, oscProximityPort);
  msg.send(udp);
  udp.endPacket();
  msg.empty();
}

void checkProximityState(float distance) {
  if (distance < 0) return;

  if (!isInProximity && distance < (PROXIMITY_THRESHOLD - HYSTERESIS)) {
    isInProximity = true;
  } else if (isInProximity && distance > (PROXIMITY_THRESHOLD + HYSTERESIS)) {
    isInProximity = false;
  }

  unsigned long currentTime = millis();
  if (isInProximity != lastProximityState &&
      (currentTime - lastStateChange) > DEBOUNCE_TIME) {

    if (isInProximity) {
      Serial.println(">>> ENTERING CLOSE PROXIMITY <<<");
    } else {
      Serial.println(">>> EXITING CLOSE PROXIMITY <<<");
    }

    lastProximityState = isInProximity;
    lastStateChange = currentTime;
  }

  // Send distance update periodically (every 200ms = 5Hz)
  static unsigned long lastProximitySend = 0;
  if (currentTime - lastProximitySend > 200) {
    sendOSCProximity(distance, isInProximity);
    lastProximitySend = currentTime;
  }
}

void sendSensorBundle(float accelX, float accelY, float accelZ, float gyroX, float gyroY, float gyroZ) {
  OSCBundle bundle;

  bundle.add("/accel/x").add(accelX);
  bundle.add("/accel/y").add(accelY);
  bundle.add("/accel/z").add(accelZ);
  bundle.add("/gyro/x").add(gyroX);
  bundle.add("/gyro/y").add(gyroY);
  bundle.add("/gyro/z").add(gyroZ);

  udp.beginPacket(oscDestIP, oscSensorPort);
  bundle.send(udp);
  udp.endPacket();
  bundle.empty();
}

// ===== BLE CALLBACK =====
class MyAdvertisedDeviceCallbacks: public BLEAdvertisedDeviceCallbacks {
  void onResult(BLEAdvertisedDevice advertisedDevice) {
    if (advertisedDevice.haveName() &&
        String(advertisedDevice.getName().c_str()).indexOf(DEVICE_NAME) >= 0) {

      int rssi = advertisedDevice.getRSSI();
      float rawDistance = calculateDistance(rssi);
      float distance = smoothDistance(rawDistance);

      checkProximityState(distance);

      unsigned long currentTime = millis();
      if (currentTime - lastPrintTime >= PRINT_INTERVAL) {
        Serial.print("🔍 BLE: ");
        Serial.print(advertisedDevice.getName().c_str());
        Serial.print(" | RSSI: ");
        Serial.print(rssi);
        Serial.print(" dBm | Distance: ");
        Serial.print(distance, 2);
        Serial.print("m | ");
        Serial.println(isInProximity ? "CLOSE" : "FAR");
        lastPrintTime = currentTime;
      }
    }
  }
};

// ===== BLE SCANNING TASK =====
void BLEScanTask(void * parameter) {
  for(;;) {
    if (!bleScanInProgress) {
      bleScanInProgress = true;
      BLEScanResults* foundDevices = pBLEScan->start(1, false);
      pBLEScan->clearResults();
      bleScanInProgress = false;
    }
    delay(50);
  }
}

void setup() {
  Serial.begin(115200);
  delay(1000);

  Serial.println("\n========================================");
  Serial.println("Wobble Unified - Receiver 2 BACKUP (White B)");
  Serial.println("BLE Proximity + LSM6DSOX Sensor");
  Serial.println("QT Py ESP32-S3");
  Serial.println("========================================\n");

  // Connect to WiFi
  Serial.print("Connecting to WiFi: ");
  Serial.println(ssid);
  WiFi.begin(ssid, password);

  int attempts = 0;
  while (WiFi.status() != WL_CONNECTED && attempts < 20) {
    delay(500);
    Serial.print(".");
    attempts++;
  }

  if (WiFi.status() == WL_CONNECTED) {
    Serial.println("\n✓ WiFi connected!");
    Serial.print("  IP Address: ");
    Serial.println(WiFi.localIP());
  } else {
    Serial.println("\n✗ WiFi connection failed!");
    while (1) delay(10);
  }

  // Start UDP for OSC
  udp.begin(oscLocalPort);
  Serial.print("  OSC Local Port: ");
  Serial.println(oscLocalPort);
  Serial.print("  OSC Destination: ");
  Serial.println(oscDestIP);
  Serial.print("    - Proximity: port ");
  Serial.print(oscProximityPort);
  Serial.println(" → Python Unified Processor (BACKUP)");
  Serial.print("    - Sensor: port ");
  Serial.print(oscSensorPort);
  Serial.println(" → Python Unified Processor (BACKUP)");
  Serial.println();

  // Initialize LSM6DSOX sensor
  Wire1.begin(SDA1_PIN, SCL1_PIN);

  Serial.println("Initializing LSM6DSOX sensor...");
  if (!sox.begin_I2C(0x6A, &Wire1)) {
    Serial.println("  Trying alternate address 0x6B...");
    if (!sox.begin_I2C(0x6B, &Wire1)) {
      Serial.println("✗ LSM6DSOX not found!");
      while (1) delay(10);
    }
  }

  Serial.println("✓ LSM6DSOX Found!\n");

  sox.setAccelDataRate(LSM6DS_RATE_104_HZ);
  sox.setGyroDataRate(LSM6DS_RATE_104_HZ);

  // Initialize BLE
  Serial.println("Initializing BLE scanner...");
  BLEDevice::init("QTPy_Receiver2_White_B");
  pBLEScan = BLEDevice::getScan();
  pBLEScan->setAdvertisedDeviceCallbacks(new MyAdvertisedDeviceCallbacks());
  pBLEScan->setActiveScan(true);
  pBLEScan->setInterval(100);
  pBLEScan->setWindow(99);

  Serial.println("✓ BLE Scanner initialized!\n");

  // Start BLE scanning on Core 0
  xTaskCreatePinnedToCore(
    BLEScanTask,
    "BLETask",
    10000,
    NULL,
    1,
    &BLETask,
    0
  );

  Serial.println("✓ BLE Task started on Core 0\n");

  Serial.println("System Configuration (BACKUP BOARD):");
  Serial.println("  Port 8102: /proximity/distance (distance + in_range)");
  Serial.println("  Port 8106: Sensor bundle (25Hz)");
  Serial.println("    - /accel/x, /accel/y, /accel/z");
  Serial.println("    - /gyro/x, /gyro/y, /gyro/z");
  Serial.println("  Compatible with all scenes (0, 1, 2)");
  Serial.println("\n========================================");
  Serial.println("System ready! (BACKUP MODE)");
  Serial.println("========================================\n");
}

void loop() {
  unsigned long currentTime = millis();

  // Send sensor data at regular intervals (runs on Core 1)
  if (currentTime - lastSensorSendTime >= SENSOR_UPDATE_INTERVAL) {
    lastSensorSendTime = currentTime;

    sensors_event_t accel;
    sensors_event_t gyro;
    sensors_event_t temp;
    sox.getEvent(&accel, &gyro, &temp);

    sendSensorBundle(
      accel.acceleration.x, accel.acceleration.y, accel.acceleration.z,
      gyro.gyro.x, gyro.gyro.y, gyro.gyro.z
    );
  }

  delay(1);
}
