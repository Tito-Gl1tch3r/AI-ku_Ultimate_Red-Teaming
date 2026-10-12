#include "led.h"
#include "config.h"

#if LED_ENABLED

#if LED_TYPE_NEOPIXEL
#include <Adafruit_NeoPixel.h>
#ifndef LED_NEOPIXEL_ORDER
#define LED_NEOPIXEL_ORDER NEO_GRB
#endif
#ifndef LED_CORRECT_R
#define LED_CORRECT_R 255
#endif
#ifndef LED_CORRECT_G
#define LED_CORRECT_G 255
#endif
#ifndef LED_CORRECT_B
#define LED_CORRECT_B 255
#endif
#ifndef LED_USE_GAMMA
#define LED_USE_GAMMA 0
#endif
static Adafruit_NeoPixel pixel(LED_NUM_PIXELS, LED_PIN, LED_NEOPIXEL_ORDER + NEO_KHZ800);

static uint8_t corrected(uint8_t value, uint8_t scale) {
  uint16_t v = (static_cast<uint16_t>(value) * scale) / 255;
#if LED_USE_GAMMA
  return Adafruit_NeoPixel::gamma8(static_cast<uint8_t>(v));
#else
  return static_cast<uint8_t>(v);
#endif
}

namespace led {
void begin() {
  pixel.begin();
  pixel.setBrightness(LED_BRIGHTNESS);
  pixel.show();
}
void setColor(int r, int g, int b) {
  uint8_t rr = corrected(constrain(r, 0, 255), LED_CORRECT_R);
  uint8_t gg = corrected(constrain(g, 0, 255), LED_CORRECT_G);
  uint8_t bb = corrected(constrain(b, 0, 255), LED_CORRECT_B);
  for (uint8_t i = 0; i < LED_NUM_PIXELS; ++i) {
    pixel.setPixelColor(i, pixel.Color(rr, gg, bb));
  }
  pixel.show();
}
bool enabled() { return true; }
}
#else
namespace led {
void begin() {
  pinMode(LED_PIN_R, OUTPUT);
  pinMode(LED_PIN_G, OUTPUT);
  pinMode(LED_PIN_B, OUTPUT);
}
void setColor(int r, int g, int b) {
#if LED_ANODE
  r = 255 - r; g = 255 - g; b = 255 - b;
#endif
  analogWrite(LED_PIN_R, r);
  analogWrite(LED_PIN_G, g);
  analogWrite(LED_PIN_B, b);
}
bool enabled() { return true; }
}
#endif

#else

namespace led {
void begin() {}
void setColor(int, int, int) {}
bool enabled() { return false; }
}

#endif
