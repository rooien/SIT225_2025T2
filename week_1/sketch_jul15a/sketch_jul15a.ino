void setup() {
  Serial.begin(9600);
  randomSeed(analogRead(0));  // Seed random number generator
}

void loop() {
  // Step 1: Wait for Python to send a number
  if (Serial.available() > 0) {
    int blinkCount = Serial.parseInt();  // Read integer

    // Step 2: Blink built-in LED (on pin 13) that many times
    for (int i = 0; i < blinkCount; i++) {
      digitalWrite(LED_BUILTIN, HIGH);  // Turn LED ON
      delay(500);// Wait 0.5 seconds
      digitalWrite(LED_BUILTIN, LOW);// Turn LED OFF
      delay(500);// Wait another 0.5 seconds
    }

    // Step 3: Send a random number (1–5) back to Python
    int waitTime = random(1, 6);
    Serial.println(waitTime);  // Send back to Python
  }
}
