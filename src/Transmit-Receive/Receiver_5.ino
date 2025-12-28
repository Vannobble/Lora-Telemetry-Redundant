#include <SPI.h>
#include <LoRa.h>

#define SS 10
#define RST 9
#define DIO0 2

#define LORA_FREQ        390E6
#define SPREADING_FACTOR 10
#define SIGNAL_BANDWIDTH 62.5E3
#define CODING_RATE      4

float altitude = 0.0;
int32_t latitude = 0;
int32_t longitude = 0;
float battery_voltage = 0.0;
int battery_remaining = 0;
String status_text = "OK";

String expectedNext = "ALT";
unsigned long lastDataTime = 0;
unsigned long cycleStartTime = 0;
unsigned long cycleEndTime = 0;
float RSSI = 0.0;
float SNR = 0.0;

void setup() {
  Serial.begin(115200);
  Serial.println("LoRa Receiver Started");

  LoRa.setPins(SS, RST, DIO0);
  if (!LoRa.begin(LORA_FREQ)) {
    Serial.println("LoRa init failed!");
    while (1);
  }

  LoRa.setSpreadingFactor(SPREADING_FACTOR);
  LoRa.setSignalBandwidth(SIGNAL_BANDWIDTH);
  LoRa.setCodingRate4(CODING_RATE);

  Serial.println("LoRa Ready, waiting for packets...");
}

void loop() {
  int packetSize = LoRa.parsePacket();

  if (packetSize) {
    String receivedData = "";
    while (LoRa.available()) {
      receivedData += (char)LoRa.read();
    }
    processData(receivedData);
    RSSI += float(LoRa.packetRssi());
    SNR += LoRa.packetSnr();
    lastDataTime = millis();
  }

  if (millis() - lastDataTime > 2000 && lastDataTime != 0) {
    expectedNext = "ALT";
    cycleStartTime = 0;
    RSSI = 0.0;
    SNR = 0.0;
    lastDataTime = millis();
  }
}

void processData(String data) {
  data.trim();
  if (data.length() < 2) return;

  if (data.startsWith("AL") && expectedNext == "ALT") {
    altitude = data.substring(2).toFloat();
    expectedNext = "LT";
    cycleStartTime = millis();
  }
  else if (data.startsWith("LT") && expectedNext == "LT") {
    latitude = data.substring(2).toInt();
    expectedNext = "LN";
  }
  else if (data.startsWith("LN") && expectedNext == "LN") {
    longitude = data.substring(2).toInt();
    expectedNext = "BAT";
  }
  else if (data.startsWith("BV") && expectedNext == "BAT") {
    String batPart = data.substring(2);
    int commaIndex = batPart.indexOf(',');
    if (commaIndex != -1 && commaIndex < batPart.length() - 1) {
      battery_voltage = batPart.substring(0, commaIndex).toFloat();
      battery_remaining = batPart.substring(commaIndex + 1).toInt();
    }
    expectedNext = "ST";
  }
  else if (data.startsWith("ST") && expectedNext == "ST") {
    status_text = data.substring(2);
    expectedNext = "ALT";
    cycleEndTime = millis();
    unsigned long totalCycleTime = cycleEndTime - cycleStartTime;

    Serial.println("========== UAV DATA ==========");
    Serial.print("Altitude: "); Serial.print(altitude, 2); Serial.println(" m");
    Serial.print("Latitude: "); Serial.println(latitude);
    Serial.print("Longitude: "); Serial.println(longitude);
    Serial.print("Battery: "); Serial.print(battery_voltage, 2);
    Serial.print("V ("); Serial.print(battery_remaining); Serial.println("%)");
    Serial.print("Status: "); Serial.println(status_text);
    Serial.print("Cycle Time: "); Serial.print(totalCycleTime); Serial.println(" ms");
    Serial.print("Avg RSSI: "); Serial.print(RSSI / 5.0, 2); Serial.println(" dBm");
    Serial.print("Avg SNR: "); Serial.print(SNR / 5.0, 2); Serial.println(" dB");
    Serial.println("==============================");

    RSSI = 0.0;
    SNR = 0.0;
  }
  else {
    expectedNext = "ALT";
    cycleStartTime = 0;
    RSSI = 0.0;
    SNR = 0.0;
  }
}
