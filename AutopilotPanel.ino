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
  byte wrap_flag;
  bool initialised;
  long disp_val;
  long sent_val;
  Adafruit_7segment display;
} Element;

#define ELEMENTS 5

bool connected = false;

Element elements[] = {
  {"Heading °", 'H', i2cEncoderMiniLib(0x20), 0x70, 0, 359, 1, i2cEncoderMiniLib::WRAP_ENABLE},
  {"Altitude ft", 'A', i2cEncoderMiniLib(0x21), 0x71, 0, 600, 1, i2cEncoderMiniLib::WRAP_DISABLE},
  {"Speed kn", 'S', i2cEncoderMiniLib(0x22), 0x72, 0, 1000, 1, i2cEncoderMiniLib::WRAP_DISABLE},
  {"QNH mmHg", 'Q', i2cEncoderMiniLib(0x23), 0x73, 2600, 3100, 1, i2cEncoderMiniLib::WRAP_DISABLE},
  {"VSpeed 10 fpm", 'V', i2cEncoderMiniLib(0x24), 0x74, -800, 600, 5, i2cEncoderMiniLib::WRAP_DISABLE},
};

void setup() {
  Wire.begin();
  Serial.begin(115200);
  
  for (int i=0; i<ELEMENTS; i++) {
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

      for (int i=0; i<ELEMENTS; i++) {
        Element &e = elements[i];
        e.display.print(e.disp_val);
        e.display.writeDisplay();
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
    for (int i=0; i<ELEMENTS; i++) {
      Element &e = elements[i];
      if (b == e.id) {
        long val = Serial.parseInt();
        e.disp_val = val;
        e.sent_val = val;
        e.encoder.writeCounter(val);
        e.display.print(val);
        e.display.writeDisplay();
        e.initialised = true;
        break;
      }
    }
  }
}

void read_inputs() {
  for (int i=0; i<ELEMENTS; i++) {
    Element &e = elements[i];
    if (!e.initialised)
      continue;
    
    long val = e.encoder.readCounterLong();
    if (val != e.disp_val) {
      e.disp_val = val;
      e.display.print(val);
      e.display.writeDisplay();
    }
    
    if (e.sent_val != val && Serial.availableForWrite() >= 7) {
      Serial.print(e.id);
      Serial.println(val);
      e.sent_val = val;
    }
  }
  Serial.flush();
}
