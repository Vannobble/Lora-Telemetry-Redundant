#include <SPI.h>
#include <LoRa.h>
#include "C:\Users\acern\OneDrive\Documents\Arduino\libraries\c_library_v2-master\common\mavlink.h"

#define SCK     18
#define MISO    19
#define MOSI    23
#define CS      5
#define RST     14
#define DIO0    26
#define SPREADING_FACTOR 10
#define SIGNAL_BANDWIDTH 62500  
#define TX_POWER         20
#define CODING_RATE      4
#define RXD2 16
#define TXD2 17
#define LED_PIN 2   // indikator LED (bisa ubah sesuai board)

float current_altitude = 0.0;
int32_t current_latitude = 0;
int32_t current_longitude = 0;
float battery_voltage = 0.0;
int battery_remaining = 0;
char status_text[50] = "OK";
bool dataUpdated = false;
unsigned long lastSendTime = 0;
const unsigned long sendInterval = 100;
uint8_t dataSequence = 0;

void setup() {
  Serial.begin(115200);
  Serial2.begin(57600, SERIAL_8N1, RXD2, TXD2); 
  SPI.begin(SCK, MISO, MOSI, CS);
  LoRa.setPins(CS, RST, DIO0);

  pinMode(LED_PIN, OUTPUT);

  Serial.println("Initializing LoRa...");
  if (!LoRa.begin(390E6)) {
    Serial.println("Starting LoRa failed!");
    while (1);
  }

  LoRa.setTxPower(TX_POWER);
  LoRa.setSpreadingFactor(SPREADING_FACTOR);
  LoRa.setSignalBandwidth(SIGNAL_BANDWIDTH);
  LoRa.setCodingRate4(CODING_RATE);

  // === INDIKATOR DI AWAL ===
  Serial.println("LoRa transmitter initialized and ready to send data!");
  digitalWrite(LED_PIN, HIGH);
  delay(1000);  // LED nyala 1 detik
  digitalWrite(LED_PIN, LOW);
}

void loop() {
  mavlink_message_t msg;
  mavlink_status_t status;

  while (Serial2.available() > 0) {
    uint8_t c = Serial2.read();
    if (mavlink_parse_char(MAVLINK_COMM_0, c, &msg, &status)) {
      switch (msg.msgid) {
        case MAVLINK_MSG_ID_GLOBAL_POSITION_INT: {
          mavlink_global_position_int_t pos;
          mavlink_msg_global_position_int_decode(&msg, &pos);
          current_altitude = pos.relative_alt / 1000.0f;
          current_latitude = pos.lat;
          current_longitude = pos.lon;
          dataUpdated = true;
          break;
        }
        case MAVLINK_MSG_ID_SYS_STATUS: {
          mavlink_sys_status_t sys;
          mavlink_msg_sys_status_decode(&msg, &sys);
          battery_voltage = sys.voltage_battery / 1000.0f;
          battery_remaining = (sys.battery_remaining >= 0) ? sys.battery_remaining : 0;
          dataUpdated = true;
          break;
        }
        case MAVLINK_MSG_ID_STATUSTEXT: {
          mavlink_statustext_t st;
          mavlink_msg_statustext_decode(&msg, &st);
          strncpy(status_text, (char*)st.text, 40);
          status_text[40] = '\0';
          if (strlen(status_text) == 0) strcpy(status_text, "OK");
          dataUpdated = true;
          break;
        }
      }
    }
  }

  if (dataUpdated && (millis() - lastSendTime >= sendInterval)) {
    lastSendTime = millis();
    
    LoRa.beginPacket();
    char buf[50];
    
    switch (dataSequence) {
      case 0:
        snprintf(buf, sizeof(buf), "AL%.2f", current_altitude);
        break;
      case 1:
        snprintf(buf, sizeof(buf), "LT%ld", current_latitude);
        break;
      case 2:
        snprintf(buf, sizeof(buf), "LN%ld", current_longitude);
        break;
      case 3:
        snprintf(buf, sizeof(buf), "BV%.2f,%d", battery_voltage, battery_remaining);
        break;
      case 4:
        snprintf(buf, sizeof(buf), "ST%s", (strlen(status_text) > 0 && strcmp(status_text, "OK") != 0) ? status_text : "OK");
        dataUpdated = false;
        break;
    }
    
    LoRa.write((uint8_t*)buf, strlen(buf));
    LoRa.endPacket();
    dataSequence = (dataSequence + 1) % 5;
  }
}
