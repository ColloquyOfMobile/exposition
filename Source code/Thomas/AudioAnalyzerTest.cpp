/* ----------------------------------------------------------------------------
 *
 * AudioAnalyzerTest.cpp
 * 
 * Project: Gordon Pask, Colloquy of Mobiles
 * Board: Mega 2560
 * 
 * Test routine for the audio subsystem used in G. Pask, 'Colloquy of Mobiles'.
 * Five tones with frequencies of 160 Hz, 400 Hz, 1KHz, 2K5Hz and 6K25Hz are
 * generated on demand by programming timers 1, 3, 4, 5 and 2 in CTC mode. 
 * The AD converted output from the audioanalyzer modules is output on the terminal.
 * It is assumed that the modules are connected to the arduino analog inputs 
 * starting with input 0. Adjust different configurations in AudioAnalyzer.h.
 * 
 * Based on the library for audio spectrum analyzer from DFROBOT, Rev 1.3, 
 * created by Lauren Pan, Dec 5, 2012.
 * 
 * Author: Thomas Erforth 
 * ZKM | Zentrum fuer Kunst und Medien
 *       Center for Art and Media 
 * 
 * Rev 1.1
 * Created: May 26, 2026
 * History:
 * Rev 1.2, May 31, 2026: Set default frequency to 1 kHz if input frequency not in 
 *                        in range from 1 Hz to 20000 kHz
 * Rev 1.3, June 08, 2026:  Menue added
 *                          New commands: Single analyzer, Mute, Help
 *                          Handling of serial input updated
 *                          Output table restructured
 * Rev 2.0, June 16, 2026: New board MEGA2560, support of 5 audio outputs, enhanced command options
 *  
 * ----------------------------------------------------------------------------
*/

#include <AudioAnalyzer.h>

Analyzer Audio = Analyzer();

// 2D array for the values read from the analyzer modules
uint16_t FreqVals[NrOfModules][MAXBAND] = {0};

int main(void)
/* 
 * 
 */
{
  HWInit();

  while(1)
  {
    {
      clearScreen();
      showMessage(welcome);
      processCommands();
    }
  }

  Serial.flush();
  return 0;
}


void HWInit()
/*
 * initialize hardware instances.
 * calls the original init() function of the Arduino IDE to use platform specific
 * ressources like serial interface, millis etc.
 * caution: this also enables serveral interrupt sources like timer0 (millis, micros, delay)
 * and UART (serial interface) which may have an influence on the overall timing.
 */
{
  init();     // defined in Arduino platform, needed to get system working
	            // wo Arduino IDE

  Serial.begin(BAUDRATE);
  Audio.Init();   //Init audio analyzer module 

  // timer outputs
  pinMode(AUDIO_160, OUTPUT); // T1 OC1A
  pinMode(AUDIO_400, OUTPUT); // T3 OC3A
  pinMode(AUDIO_1K, OUTPUT);  // T4 OC4A
  pinMode(AUDIO_2K5, OUTPUT); // T5 OC5A
  pinMode(AUDIO_6K2, OUTPUT); // T2 OC2A
}


void processCommands()
/* 
 * process commands received from serial interface
*/
{
  char buffer[10];  // input buffer
  char command1;
  char command2;

  while(true)
  {
    Serial.print(F("> "));
    // read command
    readSerial(buffer, sizeof(buffer));
    command1 = buffer[0];
    command2 = buffer[1];

    // execute command
    switch (command1)
    {
      // calculator
      case 'C':
        calculator();
        Serial.println();
        break;

      // dump all or one analyzer module
      case 'A':
        showModules(command2);
        Serial.println();
        return;

      // disable timer
      case 'D':
        if (command2 == 'a')
        {
          enableDisableAll(true);
          Serial.println(); 
        }
        else
        {
          enableDisableSingle(true, command2);
          Serial.println();
        }
        break;

      // enable timer
      case 'E':
        if (command2 == 'a')
        {
          enableDisableAll(false);
          Serial.println();
        }
        else
        {
          enableDisableSingle(false, command2);
          Serial.println();
        }
        break;

      // show Info
      case 'I':
        showMessage(info);
        break;

      // help menue
      case 'H':
        showMessage(menu);
        break;
      
      default:
        break;
        //Serial.println();
    }
  }
}


void showMessage(const char* const *text)
/* display string array located in progmem
 *
 * 'text': pointer to array of pointers to string
*/
{
  // buffer to hold each string copied from PROGMEM.
  // MESSAGE_SIZE must be large enough for the longest expected string (including '\0')!.
  char buffer[MESSAGE_SIZE] = {0};

  // iterate over the array of string pointers stored in PROGMEM.
  // stop when a nullptr pointer is encountered. pgm_read_ptr reads a pointer from PROGMEM.
  for (uint8_t i = 0; pgm_read_ptr(&text[i]) != nullptr; i++)
    {
      // pointer that will point to the buffer after copying. Initialized defensively.
      char *message = nullptr;

      // copy the null-terminated string from PROGMEM into RAM buffer.
      // pgm_read_ptr(&text[i]) returns the pointer to the PROGMEM string.
      // static_cast<char*> converts the read pointer type for strcpy_P. 
      message =  strcpy_P(buffer, static_cast<char *>(pgm_read_ptr(&text[i])));

      Serial.println(message);
    }
  Serial.println();
}


uint8_t readSerial(char * buffer, uint8_t bufSize)
/*
 * read up to 'bufSize - 1' bytes from the serial interface and NUL-terminate the result.
 * note: configure the terminal to use 'local echo' and to 'send on Enter'.
 * 
 * 'buffer': pointer to character buffer
 * 'bufSize': buffer size
 * 
 * return: 'len': number of valid bytes in buffer
*/
{
  uint8_t len;
  
  // reset the hardware serial to clear any stale state or buffered bytes.
  // Serial.available() can report 0 even if a CR/LF remains; ending and
  // restarting Serial discards internal buffers so we start with a clean input state.
  Serial.end();
  Serial.begin(BAUDRATE);

  if (bufSize == 0) return 0;

  while (!Serial.available()){ /* spin until data arrives */}
  
  // bufSize - 1: reserve space for '\0
  len = Serial.readBytesUntil('\n', buffer, bufSize - 1);
  
  // ensure the buffer is NUL-terminated.
  buffer[len] = '\0';
  
  return len;
}


void enableDisableSingle(boolean disable, uint8_t timer)
{
  /*  
   * Enable or disable timer 1, 2, 3, 4, or 5
   * 'mute: mode of operation, false: enable timer,  true: disable timer
   * 'timer': number of timer to be enabled or disabled, n = 1 - 5
  */
  
  // ascii to int
  timer -= '0'; 
  // clamp timer to 1 - 5
  timer = ((timer < 1) | (timer > 5)) ? 1 : timer;
  
  if (disable)  Serial.print(F("< Disable timer "));
  else          Serial.print(F("< Enable timer "));
  Serial.println(timer);

  // reset timer control registers (clear TCCRxA and TCCRxB for the selected timer)
  *TIMERS[(2 * timer) - 2] = 0;    // TCCRxA
  *TIMERS[(2 * timer) - 1] = 0;    // TCCRxB
  
  // If disable flag is set, leave registers cleared and return (timer disabled)
  if (disable) return;

  // 8-bit timer 2 register setting differs from 16 bit timer settings
  if (timer == 2)
  {
    // configure 8 bit timer 2
    TCCR2A |= ((1 << COM2A0) | (1 << WGM21));       // toggle OC2A on Compare Match | set CTC mode
    TCCR2B |= (static_cast<int>(presBits8::DIV8));  // prescaler 8
    OCR2A = static_cast<uint8_t>(OCRVALS16[1]);     // ~ 6250 Hz, calculated: 9F
                                                    // note: value cast to uint8_t because timer2 is 8-bit.
  }
  else
  {
    // configure 16 bit timer 1, 3, 4, or 5
    *TIMERS[(2 * timer) - 2] |= (1 << COM1A0);                                          // TCCRA: Toggle OCxA on Compare Match
    *TIMERS[(2 * timer) - 1] |= ((1 << WGM12) | static_cast<int>(presBits16::DIV1));    // TCCRB: CTC mode | prescaler 1
    *OCR16[timer - 1] = OCRVALS16[timer - 1];
  }
}


void enableDisableAll(boolean disable)
{
  /*
   * Enable or disable all timers 1, 2, 3, 4, and 5
   * 'disable': mode of operation, false: enable all timers, true: disable all timers
  */

  if (disable)    Serial.println(F("< Disable five timers"));
  else            Serial.println(F("< Enable five timers"));

  // reset and stop timers (clear TCCRxA/TCCRxB for every timer)
  for (uint8_t i = 0; i < sizeof(TIMERS) / sizeof(TIMERS[0]); i ++) { *TIMERS[i] = 0;}
  // if disable flag set, leave timers cleared and return
  if (disable) return;
  
  // configure timer mode and prescaler
  // 16 bit timers 1, 3, 4, 5

  // TCCRxA / COMxA1:0 = 01, toggle OCnA/OCnB/OCnC on compare match
  // COM1A1 COM1A0 COM1B1 COM1B0 COM1C1 COM1C0 WGM11 WGM10 TCCR1A
  //    0     1       0       0     0       0     0     0     0 = 0X40

  // TCCRxB / WGMn3:2 = 01,  clear timer on compare match (CTC) mode
  // TCCRxB / CSx2:0 = 001,   prescaler 1 for all 16 bit timers
  // ICNC1 ICES1  –  WGM13 WGM12 CS12 CS11 CS10 
  //    0     0   0     0     1    0    0    1  = 0X09

  for (uint8_t i = 0; i < sizeof(TIMERS) / sizeof(TIMERS[0]); i += 2)
  {
    if(i == 2) continue;    //  skip timer2 registers here — timer2 is an 8-bit timer with different flags
    *TIMERS[i] |= (1 << COM1A0);                                              // TCCRxA: Toggle OCxA on Compare Match
    *TIMERS[i+1] |= ((1 << WGM12) | static_cast<uint8_t>(presBits16::DIV1));  // TCCRxB: CTC mode | prescaler 1
  }

  // 8 bit timer 2 (configuration differ from 16 bit timers)

  // TCCRxA / COMxA1:0 = 01, toggle OCnA/OCnB/OCnC on compare match
  // TCCRxA / WGMn1:0 = 10, clear timer on compare match (CTC) mode
  // COM2A1 COM2A0 COM2B1 COM2B0  –    –   WGM21 WGM20
  //    0       1     0      0    0    0     1      0  = 0X42

  // TCCRxB / CSx2:0 = 010, prescaler 8
  //  FOC2A FOC2B   –   –   WGM22 CS22 CS21 CS20 
  //    0     0     0   0     0     0     1   0 = 0X02

  TCCR2A |= ((1 << COM2A0) | (1 << WGM21));         // TCCR2A: Toggle OC2A on Compare Match | CTC mode
  TCCR2B |= static_cast<uint8_t>(presBits8::DIV8);  // TCCR2B: prescaler 8

  // Output Compare Register A
  // 16 bit timers
  for (uint8_t i = 0; i < sizeof(OCR16) / sizeof(OCR16[0]); i++)
  {
    *OCR16[i] = OCRVALS16[i];
  }
  
  // 8-bit timer2 compare value (use the value chosen for timer index 1 in OCRVALS16 array)
  // Cast to uint8_t because OCR2A is 8-bit.
  OCR2A = static_cast<uint8_t>(OCRVALS16[1]); // 6250 Hz, calculated: 9F
}


void calculator(void)
{
  /*
   * calculate ocr and prescaler values for both 16 and 8 bit timers running in CTC mode
   * 
   */

  // prescaler values available in MEGA2560
  uint16_t presVals16[] = {1, 8, 64, 256, 1024};          // 16 bit timers
  uint16_t presVals8[] = {1, 8, 32, 64, 128, 256, 1024};  // 8bit timer

  uint32_t ocrxa_16 = 0xFFFFFFFF;
  uint16_t ocrxa_8 = 0xFFFF;
  uint8_t presIndex_16 = 0;
  uint8_t presIndex_8 = 0;

  char buffer[10];
  uint32_t frequency;
  
  Serial.print(F("> Enter desired frequency, range 1 Hz - 20000 Hz: "));
  readSerial(buffer, sizeof(buffer));
  frequency = atol(buffer);
  // clamp to 1 - 20000 Hz
  frequency = (frequency < 1 || frequency > 20000) ? 20000 : frequency; 

  // 16 bit timer
  // choose prescaler to keep OCRxA in 16-bit range
  for (uint8_t i = 0; i < (sizeof(presVals16) / sizeof(presVals16[0])); i++) 
  {
    ocrxa_16 = (F_CPU / (2 * presVals16[i] * frequency)) - 1;

    if (ocrxa_16 <= 0xFFFF) 
    { 
      presIndex_16 = i; 
      break; 
    }
    // no success, clamp
    else ocrxa_16 = 0xFFFF;
  }

  
  // 8 bit timer
  // choose prescaler to keep OCRxA in 8-bit range
  for (uint8_t i = 0; i < (sizeof(presVals8) / sizeof(presVals8[0])); i++) 
  {
    ocrxa_8 = (F_CPU / (2 * presVals8[i] * frequency)) - 1;

    if (ocrxa_8 <= 0xFF) 
    { 
      presIndex_8 = i;
      break; 
    }
    else ocrxa_8 = 0xFF; // clamp
  }

  Serial.println();
  Serial.print(F("< OCRxA 16 bit: "));
  Serial.print(ocrxa_16, HEX);
  Serial.print(F(", \tdivider: "));
  Serial.print(presVals16[presIndex_16], DEC);
  Serial.print(F(", \tcalculated frequency: "));
  Serial.print(F_CPU / ( 2.0 * presVals16[presIndex_16] * ( ocrxa_16 + 1)), 1);
  Serial.println(F(" Hz"));
  Serial.print(F("< OCRxA 8 bit: "));
  Serial.print(ocrxa_8, HEX);
  Serial.print(F(", \tdivider: "));
  Serial.print(presVals8[presIndex_8], DEC);
  Serial.print(F(", \tcalculated frequency: "));
  Serial.print(F_CPU / ( 2.0 * presVals8[presIndex_8] * ( ocrxa_8 + 1)), 1);
  Serial.println(F(" Hz"));
}


void showModules(char option)
/*
 * show all bands from all or a single audioanalyzer
 * 'module': module number for single output, default 0
 * 'single': true for single output, default false
*/
{ 
  uint8_t moduleNr = 0;

  // analyze option
  if (option == 'a')  // dump all
  {
    Serial.println(F("< Dump five analyzers"));
  }
  else // dump single
  {
    // char to int
    moduleNr = option -'0';
    // clamp moduleNr to 0 - 4, default is 0
    moduleNr = moduleNr > 4 ? 0 : moduleNr;  
    Serial.print(F("< Dump analyzer "));
    Serial.println(moduleNr);
  }    

  Serial.println(F("< Enter 'X' to abort action"));
  Serial.println();

  // dump analyzer readings
  while(1)
  {
    Audio.ReadFreq(FreqVals); //return 7 values of 7 bandpass filters
                              //Frequency(Hz):63  160  400  1K  2.5K  6.25K  16K
                              //FreqVal[]:     0    1    2    3    4    5    6  
    
    Serial.println(F("Module\t63 Hz\t160 Hz\t400 Hz\t1k Hz\t2.5k Hz\t6.25kHz\t16k Hz")); 
    Serial.println("---------------------------------------------------------------");
                             
    for (uint8_t module = 0; module < NrOfModules; module++)
    {
      if ((option == 'a') || (moduleNr == module)) 
      {
        Serial.print("   ");
        Serial.print(module);
        Serial.print("\t");
      }
      
      for(uint8_t band = 0; band < MAXBAND; band++)            
      {
        if ((option != 'a') && (moduleNr != module)) break;
        Serial.print(" ");
        Serial.print(max((FreqVals[module][band]), 0)); //list the DC value of the seven bands for each module
        if(band < 6)  Serial.print("\t");
        else 
        {
          Serial.println();
          Serial.println("---------------------------------------------------------------");
        }
      }
    }
    Serial.println("");
    // Stop output
    if (Serial.read() == 'X') break;
    
    // improve readability
    //delay(2000);
  }
}


void clearScreen(void)
/*
 *
*/
{
  Serial.write(27);       // ESC command
  Serial.print("[2J");    // clear screen command
  Serial.write(27);
  Serial.print("[H");     // cursor to home command
}