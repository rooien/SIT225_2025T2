#include "arduino_secrets.h"
#include "thingProperties.h"
#include <DHT.h>

#define DHTPIN 2         // Digital pin connected to DHT sensor
#define DHTTYPE DHT22    // DHT 22 (AM2302)
DHT dht(DHTPIN, DHTTYPE);

// Local variables to read raw sensor data
float hum, temp;

// Temperature alarm settings
const float TEMP_ALARM_HIGH = 40.0;  // High temperature alarm threshold (°C)
const float TEMP_ALARM_LOW  = 10.0;  // Low temperature alarm threshold (°C)
bool alarmTriggered = false;         // Prevent repeated temp alarm triggers

// Humidity alarm settings
const float HUM_ALARM_HIGH = 80.0;   // High humidity alarm threshold (%)
const float HUM_ALARM_LOW  = 20.0;   // Low humidity alarm threshold (%)
bool humAlarmTriggered = false;      // Prevent repeated humidity alarm triggers

void setup() {
  Serial.begin(9600);
  delay(1500);  // Wait for Serial Monitor

  setDebugMessageLevel(4);
  ArduinoCloud.printDebugInfo();

  initProperties();  // Initialize cloud variables

  ArduinoCloud.begin(ArduinoIoTPreferredConnection);  // Connect to Cloud
  dht.begin();  // Initialize DHT sensor
}

void loop() {
  ArduinoCloud.update();

  hum = dht.readHumidity();
  temp = dht.readTemperature();

  if (isnan(hum) || isnan(temp)) {
    Serial.println("Failed to read from DHT22 sensor.");
    return;  // skip this loop if invalid
  }

  // Push sensor readings to Cloud variables
  humidity = hum;
  temperature = temp;

  // Temperature alarm logic (latches ON until switch resets)
  if ((temp > TEMP_ALARM_HIGH || temp < TEMP_ALARM_LOW) && !alarmTriggered) {
    tempAlarm = true;           // Trigger alarm in cloud dashboard
    alarmTriggered = true;      // Prevent repeated triggers until reset
    Serial.println("TEMPERATURE ALARM TRIGGERED! Value: " + String(temp) + " °C");
  }

  // Humidity alarm logic (latches ON until switch resets)
  if ((hum > HUM_ALARM_HIGH || hum < HUM_ALARM_LOW) && !humAlarmTriggered) {
    humidityAlarm = true;       // Trigger alarm in cloud dashboard
    humAlarmTriggered = true;   // Prevent repeated triggers until reset
    Serial.println("HUMIDITY ALARM TRIGGERED! Value: " + String(hum) + " %");
  }

  // Debug printout
  Serial.print("Temp: "); Serial.print(temperature); Serial.print(" °C | TempAlarm: "); Serial.print(tempAlarm);
  Serial.print(" | Humidity: "); Serial.print(humidity); Serial.print(" % | HumidityAlarm: "); Serial.println(humidityAlarm);

  delay(5000);  // wait 5 seconds before next read
}

/*
  Cloud variable callbacks (needed if variables are READ_WRITE)
*/
void onHumidityChange() {
  Serial.println("--onHumidityChange() called: " + String(humidity));
}

void onTemperatureChange() {
  Serial.println("--onTemperatureChange() called: " + String(temperature));
}

// Reset temperature alarm when switched OFF from dashboard
void onTempAlarmChange() {
  if (!tempAlarm) {
    alarmTriggered = false;
    Serial.println("Temperature alarm reset from dashboard");
  }
}

// Reset humidity alarm when switched OFF from dashboard
void onHumidityAlarmChange() {
  if (!humidityAlarm) {
    humAlarmTriggered = false;
    Serial.println("Humidity alarm reset from dashboard");
  }
}
