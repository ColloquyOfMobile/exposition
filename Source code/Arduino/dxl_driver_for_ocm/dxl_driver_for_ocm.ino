#include <Dynamixel2Arduino.h>

#define DEBUG_SERIAL Serial
#define DXL_SERIAL Serial1
#define BAUDRATE 57600

using namespace ControlTableItem;

const int DXL_DIR_PIN = 28;
Dynamixel2Arduino dxl(DXL_SERIAL, DXL_DIR_PIN);
unsigned long last_log = 0; // Initialize last_log variable

void setup() {
  DEBUG_SERIAL.begin(57600);
  dxl.setPortProtocolVersion(2.0f);
  dxl.begin(57600);
}

void loop() {
  // Get the first word
  // DEBUG_SERIAL.println("Waiting for command.");
  String command = readWord();
  if (command == "ping") {
    handlePing();
  }
  if (command == "set") {
    handleSet();
  }
  if (command == "get") {
    handleGet();
  }

  // Flush the serial buffer
  while (Serial.available()) {
    Serial.read();
  }
  // Add more cases for other commands as needed

  // dxl.writeControlTableItem(TORQUE_ENABLE, 1, 1);
}

void handleSet() {
  String property = readWord();
  if (property == "drive_mode") {
    handleSetDriveMode();
  }
  if (property == "torque_enable") {
    handleSetTorqueEnable();
  }
  if (property == "profile_velocity") {
    handleSetProfileVelocity();
  }
  if (property == "profile_acceleration") {
    handleSetProfileAcceleration();
  }
  if (property == "goal_position") {
    handleSetGoalPosition();
  }
}

void handleSetGoalPosition() {
  int id = readWord().toInt();
  int value = readWord().toInt();
  int result = dxl.writeControlTableItem(GOAL_POSITION, id, value);
  DEBUG_SERIAL.println(result);
}

void handleSetProfileAcceleration() {
  int id = readWord().toInt();
  int value = readWord().toInt();
  int result = dxl.writeControlTableItem(PROFILE_ACCELERATION, id, value);
  DEBUG_SERIAL.println(result);
}

void handleSetProfileVelocity() {
  int id = readWord().toInt();
  int value = readWord().toInt();
  int result = dxl.writeControlTableItem(PROFILE_VELOCITY, id, value);
  DEBUG_SERIAL.println(result);
}


void handleSetTorqueEnable() {
  int result;
  int id = readWord().toInt();
  int value = readWord().toInt();
  if (value == 0){
    result = dxl.torqueOff(id);
    }
  if (value == 1){
    result = dxl.torqueOn(id);
    }
  //int result = dxl.writeControlTableItem(TORQUE_ENABLE, id, value);
  DEBUG_SERIAL.println(result);
}

void handleSetDriveMode() {
  int id = readWord().toInt();
  int value = readWord().toInt();
  int result = dxl.writeControlTableItem(DRIVE_MODE, id, value);
  DEBUG_SERIAL.println(result);
}

void handleGet() {
  String property = readWord();
  if (property == "drive_mode") {
    handleGetDriveMode();
  }
  if (property == "temperature") {
    handleGetTemperature();
  }
  if (property == "elec_current") {
    handleGetElecCurrent();
  }
  if (property == "torque_enable") {
    handleGetTorqueEnable();
  }
  if (property == "profile_velocity") {
    handleGetProfileVelocity();
  }
  if (property == "profile_acceleration") {
    handleGetProfileAcceleration();
  }
  if (property == "goal_position") {
    handleGetGoalPosition();
  }
  if (property == "position") {
    handleGetPosition();
  }
}

void handleGetPosition() {
  int id = readWord().toInt();
  DEBUG_SERIAL.println(dxl.readControlTableItem(PRESENT_POSITION, id));
}

void handleGetGoalPosition() {
  int id = readWord().toInt();
  DEBUG_SERIAL.println(dxl.readControlTableItem(GOAL_POSITION, id));
}

void handleGetProfileAcceleration() {
  int id = readWord().toInt();
  DEBUG_SERIAL.println(dxl.readControlTableItem(PROFILE_ACCELERATION, id));
}

void handleGetProfileVelocity() {
  int id = readWord().toInt();
  DEBUG_SERIAL.println(dxl.readControlTableItem(PROFILE_VELOCITY, id));
}

void handleGetTorqueEnable() {
  int id = readWord().toInt();
  DEBUG_SERIAL.println(dxl.readControlTableItem(TORQUE_ENABLE, id));
}


void handleGetElecCurrent() {
  int id = readWord().toInt();
  DEBUG_SERIAL.println(dxl.readControlTableItem(PRESENT_CURRENT, id));
}

void handleGetTemperature() {
  int id = readWord().toInt();
  DEBUG_SERIAL.println(dxl.readControlTableItem(PRESENT_TEMPERATURE, id));
}


void handleGetDriveMode() {
  int id = readWord().toInt();
  DEBUG_SERIAL.println(dxl.readControlTableItem(DRIVE_MODE, id));
}

void handlePing() {
  String string_id = readWord();
  int id = string_id.toInt();
  DEBUG_SERIAL.println(dxl.ping(id));
}

String readWord() {
  String command = "";
  char letter;

  while (true) {
    if (Serial.available()) {
      letter = Serial.read();
      if (letter == ' ') {
        return command;
      }
      if (letter == '\n') {
        return command;
      }
      command += letter;
    }
  }
}
