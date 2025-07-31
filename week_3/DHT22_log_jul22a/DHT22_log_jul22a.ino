#include "thingProperties.h"
#include <DHT.h>

#define DHTPIN 2         // Digital pin connected to DHT sensor
#define DHTTYPE DHT22    // DHT 22 (AM2302)
DHT dht(DHTPIN, DHTTYPE);

// Local variables to read raw sensor data
float hum, temp;

void setup() {
  Serial.begin(9600);
  delay(1500);  // Wait for Serial Monitor

  initProperties();  // Initialize cloud variables

  ArduinoCloud.begin(ArduinoIoTPreferredConnection);  // Connect to Cloud
  dht.begin();  // 

  setDebugMessageLevel(2);
  ArduinoCloud.printDebugInfo();
}

void loop() {
  ArduinoCloud.update();

  hum = dht.readHumidity();
  temp = dht.readTemperature();

  if (isnan(hum) || isnan(temp)) {
    Serial.println("Failed to read from DHT22 sensor.");
    return;  // skip this loop if invalid
  }

  // Assign to cloud variables
  humidity = hum;
  temperature = temp;

  // Output to Serial Monitor
  Serial.println("Humidity: " + String(humidity) + "%, Temperature: " + String(temperature) + "°C");

  delay(5000);  // wait 5 seconds before next read
}

/*
  Optional: These functions are only needed if cloud vars are READ_WRITE
*/
void onHumidityChange()  {
  Serial.println("--onHumidityChange() called");
}

void onTemperatureChange()  {
  Serial.println("--onTemperatureChange() called");
}
