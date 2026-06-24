/* ----------------------------------------------------------------------------
 *
 * AudioAnalyzer.h
 * 
 * Project: Gordon Pask, Colloquy of mobiles
 * Board: Mega 2560
 * 
 * Include file for AudioAnalyzer Test routine
 * 
 * 
 * Author: Thomas Erforth 
 * ZKM | Zentrum fuer Kunst und Medien
 *       Center for Art and Media 
 * 
 * Rev 1.1
 * Created: May 26, 2026
 * History:
 * Rev 1.3, June 08 2026: Menues added, prototypes updated
 * Rev 2.0, June 16 2026: MEGA2560, support of 5 audio outputs / timers, menues enhanced
 *  
 * ----------------------------------------------------------------------------
*/

#ifndef AudioAnalyzer_h
#define AudioAnalyzer_h

#include <Arduino.h>

// serial speed
const uint16_t BAUDRATE = 9600;

// pin assignment, MEGA2560
  // analyzer module
const uint8_t STROBE = 4;   // common strobe output for modules, D4 / PG5 
const uint8_t RESET  = 3;   // common reset output for modules, D3 / PE5

  // timer outputs
    //16 bit
const uint8_t AUDIO_160 = 11; // D11  / PB5 / OC1A
const uint8_t AUDIO_400 = 5;  // D5   / PE3 / OC3A
const uint8_t AUDIO_1K  = 6;  // D6   / PH3 / OC4A
const uint8_t AUDIO_2K5 = 46; // D46  / PL3 / OC5A
    // 8 bit
const uint8_t AUDIO_6K2 = 10; // D10  / PB4 / OC2A

// number of modules and number of bands per module
const uint16_t MAXBAND = 7;
const uint16_t NrOfModules = 5;

// first ADC input, connect further modules in ascending order
const uint8_t ADCbase = 0;

// 16 / 8 bit timer precomputed OCR settings
constexpr uint16_t OCRVALS16[] = 
{
  0xC0F7,    // T1, 160 Hz, calculated: C34F
  0x9D,      // T2, 6250 Hz, calculated: 9F, cast to 8 bit when writing to OCR2A register
  0x4D31,    // T3, 400 Hz, calc: 4E1F
  0x1EE4,    // T4, 1000 Hz, calc: 1F3F
  0xC58,     // T5, 2500 Hz, calc: C7F
};

// TCR and OCR register adresses, 16 bit timer 1, 3, 4, 5
constexpr volatile uint8_t * const TIMERS[] = {&TCCR1A, &TCCR1B, &TCCR2A, &TCCR2B, &TCCR3A, &TCCR3B, &TCCR4A, &TCCR4B, &TCCR5A, &TCCR5B};
constexpr volatile uint16_t * const OCR16[] = {&OCR1A, nullptr, &OCR3A, &OCR4A, &OCR5A};

// prescaler values 16 bit timers, CS2:0 
enum class presBits16 
{
  STOP    = 0,
  DIV1    = 1,
  DIV8    = 2,
  DIV64   = 3,
  DIV256  = 4,
  DIV1024 = 5
};

// prescaler values 8 bit timers
enum class presBits8 
{
  STOP    = 0,
  DIV1    = 1,
  DIV8    = 2,
  DIV32   = 3,
  DIV64   = 4,
  DIV128  = 5,
  DIV256  = 6,
  DIV1024 = 7
};

// messages
constexpr uint8_t MESSAGE_SIZE = 61;    // maximum message string length.

  // welcome (maximum string length 60 bytes)
const char PROGMEM welcome_0[] = "----           Audio subsystem tester for            ----";
const char PROGMEM welcome_1[] = "----        Gordon Pask - Colloquy of Mobiles        ----";
const char PROGMEM welcome_3[] = "---- Copyright: ZKM | Zentrum fuer Kunst und Medien  ----";
const char PROGMEM welcome_4[] = "----                  Center for Art and Media       ----";
const char PROGMEM welcome_5[] = "----                                                 ----";
const char PROGMEM welcome_6[] = "----                  Enter 'H' for help             ----";

const char *const welcome[] PROGMEM = {welcome_0, welcome_1, welcome_3, welcome_4, welcome_5, welcome_6, nullptr};


  // menu (maximum string length 60 bytes)
const char PROGMEM menu_0[] = "----         Commands          ----";
const char PROGMEM menu_1[] = " C  - Calculator";
const char PROGMEM menu_2[] = " Ax - Dump analyzer (x: 0, 1, 2, 3, 4), abort: 'X'";
const char PROGMEM menu_3[] = " Aa - Dump all analyzers, abort: 'X'";
const char PROGMEM menu_4[] = " Dx - Disable timer (x: 1, 2, 3, 4, 5)";
const char PROGMEM menu_5[] = " Da - Disable all timers";
const char PROGMEM menu_6[] = " Ex - Enable timer (x: 1, 2, 3, 4, 5)";
const char PROGMEM menu_7[] = " Ea - Enable all timers";
const char PROGMEM menu_8[] = " I  - Info";
const char PROGMEM menu_9[] = " H  - Help: This table";

const char *const menu[] PROGMEM = {menu_0, menu_6, menu_7, menu_4, menu_5, menu_2, menu_3, menu_8, menu_1, menu_9, nullptr};


  // info (maximum string length 60 bytes)
const char PROGMEM info_0[] = "\t\t\tTimer Info";
const char PROGMEM info_1[] = "Timer:\t\tT1\tT3\tT4\tT5\tT2";
const char PROGMEM info_2[] = "Frequency:\t160Hz\t400Hz\t1kHz\t2k5Hz\t6k25Hz";
const char PROGMEM info_3[] = "Pin:\t\tD11\tD5\tD6\tD46\tD10";
const char PROGMEM info_4[] = "Configure terminal to: 'local echo' and 'send on enter'";

const char *const info[] PROGMEM = {info_0, info_1, info_2, info_3, info_4, nullptr};

// analyzer class from DFROBOT library adjusted for multiple modules
class Analyzer{
public:
	Analyzer();
	Analyzer(uint8_t, uint8_t);
	void Init();
	void ReadFreq(uint16_t [NrOfModules][MAXBAND]);

private:
	int _StrobePin;
	int _RSTPin;
	void RstModule();
};


// function prototypes
void HWInit(void);
void showMessage(const char* const *);
void enableDisableAll(boolean);
void enableDisableSingle(boolean, uint8_t);
uint8_t readSerial(char *, uint8_t);
void calculator(void);
void processCommands(void);
void showModules(char);
void clearScreen(void);

#endif

