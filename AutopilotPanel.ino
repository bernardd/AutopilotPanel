#include "Adafruit_LEDBackpack.h"
#include <i2cEncoderMiniLib.h>

#define LED_ADDRESS 0x70
#define RE_ADDRESS 0x20

typedef struct Element {
  const char* name;
  const char id;
  i2cEncoderMiniLib encoder;
  byte display_address;
  long min;
  long max;
  long step;
  byte decimal_pos;
  byte wrap_flag;
  bool initialised;
  long disp_val;
  long sent_val;
  Adafruit_7segment display;
} Element;

#define ELEMENTS 5

bool connected = false;

Element elements[] = {
  // Name           ID   RE address               LED   Min   Max   Inc Dec Wrap
  {"QNH mmHg",      'Q', i2cEncoderMiniLib(0x20), 0x70, 2600, 3100, 1,  1,  i2cEncoderMiniLib::WRAP_DISABLE},
  {"Heading °",     'H', i2cEncoderMiniLib(0x23), 0x72, 0,    359,  1,  0,  i2cEncoderMiniLib::WRAP_ENABLE},
  {"Altitude ft",   'A', i2cEncoderMiniLib(0x24), 0x71, 0,    600,  1,  3,  i2cEncoderMiniLib::WRAP_DISABLE},
  {"Speed kn",      'S', i2cEncoderMiniLib(0x22), 0x73, 0,    1000, 1,  0,  i2cEncoderMiniLib::WRAP_DISABLE},
  {"VSpeed 10 fpm", 'V', i2cEncoderMiniLib(0x21), 0x74, -800, 600,  5,  0,  i2cEncoderMiniLib::WRAP_DISABLE},
};

void setup() {
  Wire.begin();
  Serial.begin(115200);
  
  for (int i = 0; i < ELEMENTS; i++) {
    Element &e = elements[i];
    e.initialised = false;
    e.display.begin(e.display_address);
    e.display.printError();
    e.display.writeDisplay();
    setup_encoder(e);
  }
}

void loop() {
  if (!connected)
    connect();
  else
    main_loop();
}

void main_loop() {
  read_updates();
  read_inputs();
}

void connect() {
  if (Serial.available()) {
    byte b = Serial.read();
    if (b == 'C') {
      Serial.write('C');
      Serial.flush();
      connected = true;
 
      for (int i = 0; i < ELEMENTS; i++) {
        update_display(elements[i]);
      }
    }
  }
}

void setup_encoder(Element &e) {
  e.encoder.begin(e.wrap_flag | i2cEncoderMiniLib::DIRE_RIGHT | i2cEncoderMiniLib::RMOD_X1);
  e.encoder.writeMin(e.min);
  e.encoder.writeMax(e.max);
  e.encoder.writeStep(e.step); 
  e.encoder.writeCounter(e.min);
}

void read_updates() {
  while (Serial.available()) {
    byte b = Serial.read();
    for (int i = 0; i < ELEMENTS; i++) {
      Element &e = elements[i];
      if (b == e.id) {
        long val = Serial.parseInt();
        e.disp_val = val;
        e.sent_val = val;
        e.encoder.writeCounter(val);
        update_display(e);
        e.initialised = true;
        break;
      }
    }
  }
}

void read_inputs() {
  for (int i = 0; i < ELEMENTS; i++) {
    Element &e = elements[i];
    if (!e.initialised) {
      continue;
    }

    long val = e.encoder.readCounterLong();
    if (val != e.disp_val) {
      e.disp_val = val;
      update_display(e);
    }

    if (e.sent_val != val && Serial.availableForWrite() >= 7) {
      Serial.print(e.id);
      Serial.println(val);
      e.sent_val = val;
    }
  }
  Serial.flush();
}

int pos;
void update_display(Element &e) {
  int val = e.disp_val;
  bool negative = false;
  
  if (val < 0) {
    val = -val;
    negative = true;
  }
  
  pos = 4;

  // Write the digits
  for (; pos >= 0; dec_pos()) {
    e.display.writeDigitNum(pos, val % 10, e.decimal_pos == pos);
    
    if ((val /= 10) == 0) {
      break;
    }
  }

  // Add leading 0s until we have a whole number
  while (e.decimal_pos && (pos > e.decimal_pos)) {
    dec_pos();
    e.display.writeDigitNum(pos, 0, e.decimal_pos == pos);
  }

  // Add a -ve sign if required
  if (pos >= 0 && negative) {
    e.display.writeDigitRaw(dec_pos(), 0x40); // Minus sign
  }

  // Blank the rest of the display
  while (pos >= 0) {
    e.display.writeDigitRaw(dec_pos(), 0);
  }
  
  e.display.writeDisplay();
}

int dec_pos() {
  if (pos == 3) {
    pos = 1;
  } else {
    pos--;
  }
  return pos;
}
