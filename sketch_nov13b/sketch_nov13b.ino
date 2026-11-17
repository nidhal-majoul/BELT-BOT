const int PIN_DIR = 8;
const int PIN_PWM = 9;
const int PIN_EN  = 10;

void setup() {
  pinMode(PIN_DIR, OUTPUT);
  pinMode(PIN_PWM, OUTPUT);
  pinMode(PIN_EN, OUTPUT);

  digitalWrite(PIN_EN, HIGH);   // encender el driver
  digitalWrite(PIN_DIR, HIGH);  // sentido 1
  analogWrite(PIN_PWM, 150);    // velocidad media
  delay(3000);

  analogWrite(PIN_PWM, 0);      // frenar antes de cambiar de sentido
  delay(300);
  digitalWrite(PIN_DIR, LOW);   // sentido 2
  analogWrite(PIN_PWM, 150);
  delay(3000);

  digitalWrite(PIN_EN, LOW);    // parar
}

void loop() {}