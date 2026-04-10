/*
 * Wobble Unified - Transmitter (Purple Rocker)
 * Adafruit QT Py ESP32-S3
 * 
 * This board:
 * - Broadcasts BLE beacon for proximity detection (for both receivers)
 * - Sends LSM6DSOX sensor data via OSC to port 8005
 * 
 * Compatible with all three scenes (Scene 0, Scene 1, Scene 2)
 * Python processor handles scene-specific logic
 */

// ===== WIFI & OSC CONFIGURATION =====
const char* ssid = "Dr.Wifi";
const char* password = "IthurtswhenIP1800";
const char* oscDestIP = "192.168.50.201";     // Your laptop IP
const int oscSensorPort = 8005;               // Port for LSM6DSOX data → Python
const int oscLocalPort = 9005;                // Local port for OSC

// ===== BLE INCLUDES =====
#include <BLEDevice.h>
#include <BLEUtils.h>
#include <BLEServer.h>

// ===== WIFI & OSC INCLUDES =====
#include <WiFi.h>
#include <WiFiUdp.h>
#include <OSCBundle.h>

// ===== SENSOR INCLUDES =====
#include <Adafruit_LSM6DSOX.h>
#include <Wire.h>

// ===== BLE CONFIGURATION =====
#define DEVICE_NAME "QTPy_ESP32"
#define SERVICE_UUID "4fafc201-1fb5-459e-8fcc-c5c9c331914b"

// ===== LSM6DSOX CONFIGURATION =====
#define SDA1_PIN 41
#define SCL1_PIN 40
#define SENSOR_UPDATE_INTERVAL 40  // 25Hz sensor update rate

// ===== GLOBAL VARIABLES =====
BLEServer* pServer;
Adafruit_LSM6DSOX sox;
WiFiUDP udp;
unsigned long lastSensorSendTime = 0;

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

void setup() {
  Serial.begin(115200);
  delay(1000);
  
  Serial.println("\n========================================");
  Serial.println("Wobble Unified - Transmitter (Purple)");
  Serial.println("BLE Transmitter + LSM6DSOX Sensor");
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
  Serial.print(oscDestIP);
  Serial.print(":");
  Serial.print(oscSensorPort);
  Serial.println(" → Python Unified Processor");
  Serial.println();
  
  // Initialize LSM6DSOX sensor
  Wire1.begin(SDA1_PIN, SCL1_PIN);
  
  Serial.println("Initializing LSM6DSOX sensor...");
  Serial.print("  SDA1: GPIO ");
  Serial.println(SDA1_PIN);
  Serial.print("  SCL1: GPIO ");
  Serial.println(SCL1_PIN);
  
  if (!sox.begin_I2C(0x6A, &Wire1)) {
    Serial.println("  Trying alternate address 0x6B...");
    if (!sox.begin_I2C(0x6B, &Wire1)) {
      Serial.println("✗ LSM6DSOX not found!");
      while (1) delay(10);
    }
  }
  
  Serial.println("✓ LSM6DSOX Found!\n");
  
  // Configure sensor
  sox.setAccelDataRate(LSM6DS_RATE_104_HZ);
  sox.setGyroDataRate(LSM6DS_RATE_104_HZ);
  
  // Initialize BLE
  Serial.println("Initializing BLE transmitter...");
  BLEDevice::init(DEVICE_NAME);
  pServer = BLEDevice::createServer();
  
  BLEService *pService = pServer->createService(SERVICE_UUID);
  pService->start();
  
  BLEAdvertising *pAdvertising = BLEDevice::getAdvertising();
  pAdvertising->addServiceUUID(SERVICE_UUID);
  pAdvertising->setScanResponse(true);
  pAdvertising->setMinPreferred(0x06);
  pAdvertising->setMinPreferred(0x12);
  
  esp_ble_tx_power_set(ESP_BLE_PWR_TYPE_ADV, ESP_PWR_LVL_P9);
  
  BLEAdvertisementData advertisementData;
  advertisementData.setName(DEVICE_NAME);
  advertisementData.setCompleteServices(BLEUUID(SERVICE_UUID));
  pAdvertising->setAdvertisementData(advertisementData);
  
  BLEAdvertisementData scanResponseData;
  scanResponseData.setName(DEVICE_NAME);
  pAdvertising->setScanResponseData(scanResponseData);
  
  BLEDevice::startAdvertising();
  
  Serial.println("✓ BLE Transmitter started!");
  Serial.print("  Device Name: ");
  Serial.println(DEVICE_NAME);
  Serial.println();
  
  Serial.println("System Configuration:");
  Serial.println("  - BLE beacon: Broadcasting for proximity detection");
  Serial.println("  - Sensor data: Port 8005 → Python Unified Processor");
  Serial.println("    /accel/x, /accel/y, /accel/z");
  Serial.println("    /gyro/x, /gyro/y, /gyro/z");
  Serial.println("  - Compatible with all scenes (0, 1, 2)");
  Serial.println("\n========================================");
  Serial.println("System ready!");
  Serial.println("========================================\n");
}

void loop() {
  unsigned long currentTime = millis();
  
  // Send sensor data at regular intervals
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
    
    // Optional debug output (prints every ~1 second)
    static int printCounter = 0;
    if (printCounter++ % 25 == 0) {
      Serial.print("📡 Sensor bundle sent | Accel: ");
      Serial.print(accel.acceleration.x, 2);
      Serial.print(", ");
      Serial.print(accel.acceleration.y, 2);
      Serial.print(", ");
      Serial.print(accel.acceleration.z, 2);
      Serial.print(" | Gyro: ");
      Serial.print(gyro.gyro.x, 2);
      Serial.print(", ");
      Serial.print(gyro.gyro.y, 2);
      Serial.print(", ");
      Serial.println(gyro.gyro.z, 2);
    }
  }
  
  delay(10);
}
