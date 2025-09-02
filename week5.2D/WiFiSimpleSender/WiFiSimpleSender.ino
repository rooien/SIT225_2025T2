/*
  ArduinoMqttClient - WiFi Simple Sender

  This example connects to a MQTT broker and publishes a message to
  a topic once a second.

  The circuit:
  - Arduino MKR 1000, MKR 1010 or Uno WiFi Rev2 board

  This example code is in the public domain.
*/

#include <Arduino_LSM6DS3.h>
#include <ArduinoMqttClient.h>
#include <WiFiNINA.h>
#include "arduino_secrets.h"

///////please enter your sensitive data in the Secret tab/arduino_secrets.h
char ssid[] = SECRET_SSID;    // your network SSID (name)
char pass[] = SECRET_PASS;    // your network password (use for WPA, or use as key for WEP)

// To connect with SSL/TLS:
// 1) Change WiFiClient to WiFiSSLClient.
// 2) Change port value from 1883 to 8883.
// 3) Change broker value to a server with a known SSL/TLS root certificate 
//    flashed in the WiFi module.

// ---- HiveMQ Cloud (TLS) ----

WiFiSSLClient wifiClient;
MqttClient mqttClient(wifiClient);

const char broker[] = "a215303a3a274a7d801eca40560e1134.s1.eu.hivemq.cloud";
int        port     = 8883;
const char topic[]  = "sit225/gyroscope";

const long interval = 1000;
unsigned long previousMillis = 0;

int count = 0;

void setup() {
  Serial.begin(9600);
  while (!Serial) {}  // ok for Nano 33 IoT

  // Init IMU
  if (!IMU.begin()) {
    Serial.println("ERROR: IMU init failed");
    while (true) {}
  }

  // attempt to connect to WiFi network:
Serial.print("Attempting to connect to WPA SSID: ");
Serial.println(ssid);
while (WiFi.begin(ssid, pass) != WL_CONNECTED) {
  // failed, retry
  Serial.print(".");
  delay(5000);
  }

  Serial.println("You're connected to the network");
  Serial.println();

  // You can provide a unique client ID, if not set the library uses Arduino-millis()
  // Each client must have a unique client ID
  // mqttClient.setId("clientId");

  // You can provide a username and password for authentication
  // mqttClient.setUsernamePassword("username", "password");

  mqttClient.setUsernamePassword("sit225user", "Aa00000*");
  Serial.print("Attempting to connect to the MQTT broker: ");
  Serial.println(broker);

  if (!mqttClient.connect(broker, port)) {
    Serial.print("MQTT connection failed! Error code = ");
    Serial.println(mqttClient.connectError());

    while (1);
  }

  Serial.println("You're connected to the MQTT broker!");
  Serial.println();
}

void loop() {
  // call poll() regularly to allow the library to send MQTT keep alives which
  // avoids being disconnected by the broker
  mqttClient.poll();

  // to avoid having delays in loop, we'll use the strategy from BlinkWithoutDelay
  // see: File -> Examples -> 02.Digital -> BlinkWithoutDelay for more info
  unsigned long currentMillis = millis();
  
  if (currentMillis - previousMillis >= interval) {
    // save the last time a message was sent
    previousMillis = currentMillis;

    float gx, gy, gz;                   // degrees per second (dps)
    if (IMU.gyroscopeAvailable() && IMU.readGyroscope(gx, gy, gz)) {
      char payload[160];
      snprintf(payload, sizeof(payload),
               "{\"gx\":%.4f,\"gy\":%.4f,\"gz\":%.4f,\"t_device_ms\":%lu}",
               gx, gy, gz, millis());


    // send message, the Print interface can be used to set the message contents
    mqttClient.beginMessage(topic);   // defaults: QoS0, retain=false
    mqttClient.print(payload);
    mqttClient.endMessage();

    Serial.print("PUB "); Serial.print(topic); Serial.print(" ");
    Serial.println(payload);
  }
}
}
