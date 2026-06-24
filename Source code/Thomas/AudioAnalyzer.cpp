/* ----------------------------------------------------------------------------
 *
 * AudioAnalyzer.cpp
 * 
 * Project: Gordon Pask, Colloquy of mobiles
 * 
 * Library for AudioAnalyzer Test routine
 * Based on the library for audio spectrum analyzer from DFROBOT, Rev 1.3, 
 * created by Lauren Pan,Dec 5, 2012.
 * 
 * The library is a modified version to support 5 analyzer modules.
 * All modules are connected to the same strobe / reset output.
 * It is assumed that the modules are connected to the arduino analog inputs 
 * starting with input 0. Adjust different configurations in AudioAnalyzer.h.
 * 
 * 
 * Author: Thomas Erforth 
 * ZKM | Zentrum fuer Kunst und Medien
 *       Center for Art and Media 
 * 
 * Rev 1.0
 * Created: May 16, 2026
 * 
 * History:
 * Rev 1.1, May 31, 2026: Reset / Strobe timing optimized 
 * ----------------------------------------------------------------------------
*/

#include "AudioAnalyzer.h"

/*
 * initialize the outputs for the analyzer modules
*/
Analyzer::Analyzer(void)
{
	_StrobePin = STROBE;
	_RSTPin = RESET;
}


Analyzer::Analyzer(uint8_t StrobePin, uint8_t RstPin)
{
	_StrobePin = StrobePin;
	_RSTPin = RstPin;
}


void Analyzer::Init()
{
	pinMode(_StrobePin,OUTPUT);
	pinMode(_RSTPin,OUTPUT);
	// RstModule();
}


void Analyzer::RstModule()
/*
 * reset analyzer modules
 * timing adjusted for Atmega 328P, 16 MHz
*/
{
	digitalWrite(_StrobePin,LOW);
  digitalWrite(_RSTPin,LOW);
	digitalWrite(_RSTPin,HIGH);   // tr, reset pulse width, 100 ns min, 28 us measured
	digitalWrite(_RSTPin,LOW);
  delayMicroseconds(54);        // tRS, reset low to strobe low, 72 us min, 77 us measured
}


void Analyzer::ReadFreq(uint16_t value[NrOfModules][MAXBAND])
/*
 * read DC valuies from modules
 * input: 2 dimensional array holding the band values for each module
 */

{
  RstModule();    // always reset the multiplexer

  // initiate 10 dummy reads over all bands to speed up the decay of the inactiv bands
  
  for(uint8_t k = 0; k < (10 * MAXBAND); k++)
  {
    digitalWrite(_StrobePin,HIGH);
    delayMicroseconds(18);        // tS, strobe pulse width, 18 us min, 20 us measured
    digitalWrite(_StrobePin,LOW); // tO: output settling time 36 us min
    delayMicroseconds(36);        // needed for tO and between reads from ADC
  }

  // RstModule();    // always reset the multiplexer
  // now for each band
  for(uint8_t band = 0; band < MAXBAND; band++)
  {
    digitalWrite(_StrobePin,HIGH);
    delayMicroseconds(18);        // tS, strobe pulse width, 18 us min, 20 us measured
    digitalWrite(_StrobePin,LOW); // tO: output settling time 36 us min
    delayMicroseconds(36);       // needed for tO and between reads from ADC
      
    // read the value from corresponding module
    // assumes that all modules are connected to the ADC in contiguous sequence
    for (uint8_t module = ADCbase; module < NrOfModules; module++) {value[module][band] = analogRead(module);}
  }
}