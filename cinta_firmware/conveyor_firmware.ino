/*
  conveyor_firmware.ino
  ---------------------
  Arduino UNO firmware for the conveyor belt.
  The Arduino only OBEYS commands and REPORTS when a piece arrives.
  All the decisions are taken by Python on the PC.

  Serial: 9600 baud, one command per line (ends with '\n').

  Commands (case-insensitive):
    START        -> start the belt
    STOP         -> stop the belt
    CW           -> clockwise direction
    CCW          -> counter-clockwise direction
    SPEED <n>    -> set speed 0..255 (e.g. "SPEED 150")
    STATUS       -> ask for the current state

  Replies:
    READY                 -> sent once at startup
    OK <command>          -> command accepted
    STATUS ON|OFF CW|CCW <speed>
    PIECE                 -> a piece has just arrived at the sensor
    ERROR <reason>        -> wrong command
*/

// ---- Pins (from the conveyor wiring sheet) ----
const int PIN_DIR    = 8;   // PHASE  -> direction
const int PIN_PWM    = 9;   // PWM    -> speed
const int PIN_EN     = 10;  // NSLEEP -> turn the motor driver on/off
const int PIN_SENSOR = 2;   // infrared sensor signal

// If "CW" makes the belt turn the wrong way, change HIGH to LOW here.
const int CLOCKWISE_LEVEL = HIGH;

// ---- Conveyor state ----
bool running        = false;
bool clockwise      = true;
int  speed          = 150;
bool pieceBefore    = false;  // so we report only when the piece ARRIVES

// Applies the current state (running / speed) to the motor
void applyMotor() {
  if (running) {
    digitalWrite(PIN_EN, HIGH);
    analogWrite(PIN_PWM, speed);
  } else {
    analogWrite(PIN_PWM, 0);
    digitalWrite(PIN_EN, LOW);
  }
}

// Changes the direction safely (brakes first)
void setDirection(bool newClockwise) {
  if (newClockwise == clockwise) return;  // already going that way
  analogWrite(PIN_PWM, 0);                // brake before reversing
  delay(300);
  clockwise = newClockwise;
  digitalWrite(PIN_DIR, clockwise ? CLOCKWISE_LEVEL : !CLOCKWISE_LEVEL);
  applyMotor();                           // restore the speed
}

void sendStatus() {
  Serial.print("STATUS ");
  Serial.print(running ? "ON " : "OFF ");
  Serial.print(clockwise ? "CW " : "CCW ");
  Serial.println(speed);
}

// Reads one command line and executes it
void processCommand(String command) {
  command.trim();                         // removes spaces and '\r'
  command.toUpperCase();                  // "start" works the same as "START"
  if (command.length() == 0) return;

  if (command == "START") {
    running = true;
    applyMotor();
    Serial.println("OK START");

  } else if (command == "STOP") {
    running = false;
    applyMotor();
    Serial.println("OK STOP");

  } else if (command == "CW") {
    setDirection(true);
    Serial.println("OK CW");

  } else if (command == "CCW") {
    setDirection(false);
    Serial.println("OK CCW");

  } else if (command.startsWith("SPEED")) {
    String number = command.substring(5); // everything after "SPEED"
    number.trim();
    if (number.length() == 0) {
      Serial.println("ERROR missing speed (e.g. SPEED 150)");
      return;
    }
    speed = constrain(number.toInt(), 0, 255);
    applyMotor();
    Serial.print("OK SPEED ");
    Serial.println(speed);

  } else if (command == "STATUS") {
    sendStatus();

  } else {
    Serial.print("ERROR unknown command: ");
    Serial.println(command);
  }
}

void setup() {
  pinMode(PIN_DIR, OUTPUT);
  pinMode(PIN_PWM, OUTPUT);
  pinMode(PIN_EN, OUTPUT);
  pinMode(PIN_SENSOR, INPUT_PULLUP);      // the sensor gives LOW when it detects

  digitalWrite(PIN_DIR, CLOCKWISE_LEVEL);
  applyMotor();                           // starts stopped

  Serial.begin(9600);
  Serial.setTimeout(50);                  // don't wait 1 s when reading
  Serial.println("READY");
}

void loop() {
  // 1) Commands coming from the PC
  if (Serial.available() > 0) {
    String command = Serial.readStringUntil('\n');
    processCommand(command);
  }

  // 2) Sensor: report only at the moment the piece appears
  bool pieceNow = (digitalRead(PIN_SENSOR) == LOW);
  if (pieceNow && !pieceBefore) {
    Serial.println("PIECE");
  }
  pieceBefore = pieceNow;

  delay(10);
}
