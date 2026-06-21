// === LIBRARIES === //
#include <EEPROM.h>
#include <Wire.h>
#include <OneWire.h>
#include <Adafruit_ADS1X15.h>
#include <DallasTemperature.h>
#include "HX711.h"
#include <RTClib.h>
#include <Stepper.h>

// === CLASSES & STRUCTURES === //
struct Config {
  // Pi - Controller
  uint8_t brightnessA = 255;
  uint8_t brightnessB = 255;
  uint8_t brightnessC = 255;

  uint8_t minTargetTemp = 20;
  uint8_t maxTargetTemp = 30;

  uint8_t harvestPumpPower = 0;
  uint16_t harvestAmountMl = 200;

  float lightFadeDurS = 30.0;
  uint8_t lightPeriodH = 12;
  uint8_t darkPeriodH = 12;

  uint16_t compressorActiveMin = 10;
  uint16_t compressorRestMin = 2;

  float minPH = 6.0;
  float maxPH = 7.0;

  // Flasks Calibration
  float leftScaleZeroVal = 0.0f;
  float rightScaleZeroVal = 0.0f;

  float emptyLeftHarvestFlaskWeightVal = 0.0f;
  float ml100LeftHarvestFlaskWeightVal = 0.0f;

  float emptyRightHarvestFlaskWeightVal = 1.0f;
  float ml100RightHarvestFlaskWeightVal = 1.0f;

  bool scaleZeroValCalibrated = false, emptyFlasksCalibrated = false, ml100FlasksCalibrated = false;

  // pH Calibration
  float pH7SensorVal = 0.5f;
  float pH10SensorVal = 1.0f;

  bool normPHCalibrated = false, highPHCalibrated = false;
};
struct SystemState {
  uint32_t validSignature = 0xA11C001;

  uint32_t plannedLightSwitchTimestamp = 0;
  uint32_t plannedCompressorSwitchTimestamp = 0;

  uint32_t plannedPHMeasure = 0;
  uint32_t lastPHCalibrationTimestamp = 0;

  bool light = false, carbonizing = false;
};
struct EnvData {
  float tensoL;
  float tensoR;

  float tempOut;
  float tempIn;

  uint8_t waterSensorsBin; // Bitmask 000000(High)(Low)
  float turbidity;

  float pH;
};

// ========= PINS ========= //
// MOSFET Group 12VDC (PWM)
#define PUMP_PIN          PA0
#define LED_A_PIN         PA1
#define LED_B_PIN         PA2
#define LED_C_PIN         PA3

// MOSFET Group 5VDC
#define HEATER_PIN        PA4
#define COMPRESSOR_PIN    PA5
#define WATER_PUMP        PA6

#define I2C_DATA          PB7  // SDA
#define I2C_SCK           PB6  // SCL

#define TENSO_L_DT        PB0  // HX711 (L)
#define TENSO_L_SCK       PB1  // HX711 (L)
#define TENSO_R_DT        PA8  // HX711 (R)
#define TENSO_R_SCK       PA9  // HX711 (R)

#define TEMP_SENSOR_WIRE  PB12 // DS18B20

#define WATER_SENSOR_L    PB10 // XKC-Y25 (0/1)
#define WATER_SENSOR_H    PB11 // XKC-Y25 (0/1)

#define PH_STEPPER_1      PB2  // IN1 / Step
#define PH_STEPPER_2      PB3  // IN2 / Dir
#define PH_STEPPER_3      PB4  // IN3 / Enable
#define PH_STEPPER_4      PB5  // IN4

#define TURBIDITY_ADC_NUM 1
#define PH_ADC_NUM 0

// ========= CONSTANTS ========= //
#define ANALOG_ADC_RESOLUTION 65536
#define CONFIG_LIMIT 8192

#define RTC_ADDR 0x68
#define ADC_ADDR 0x48

#define MAX_WATER_ML 9000

#define SERIAL_BAUDRATE 115200

#define TENSO_UNITS 5
#define SAMPLE_SIZE 7

//#define PH_FLASK_STEP 0
#define PH_STEP_PER_REVOLUTION 2048
#define PH_CALIBRATION_RATE 14 * 86400

// ========= OBJECTS & VARIABLES ========= //
Config conf;
SystemState systemState;
EnvData environmentData;

HX711 scaleL;
HX711 scaleR;

RTC_DS3231 rtc;

Stepper pHStepper(PH_STEP_PER_REVOLUTION, PH_STEPPER_1, PH_STEPPER_2, PH_STEPPER_3, PH_STEPPER_4);

OneWire oneWire(TEMP_SENSOR_WIRE);
DallasTemperature tempSensors(&oneWire);
DeviceAddress insideThermometer, outsideThermometer;

Adafruit_ADS1115 analogADC;

bool innerTempSensorInitialized = false, outerTempSensorInitialized = false;
bool rtcValid = true;

uint32_t lastPingCheck;
float pingDelay = 0;
bool is_connected = false;

uint32_t lastEnvUpdated;

uint32_t startSwitchTime;
bool switching = false;

bool harvestPumpActive = false;

uint32_t startWaterFlowTimestamp = 0;
bool isWaterFlow = false;

// ========= FUNCTIONS ========= //
// - Special -
constexpr unsigned int string_hash(const char* str, int h = 0) {
    return !str[h] ? 5381 : (string_hash(str, h+1) * 33) ^ str[h];
}

// - Sensors -
void initSensors() {
  // RTC DS3231
  if (!rtc.begin()) { 
    log(String(F("(ERROR) RTC not found!"))); 
    rtcValid = false; 
  } else { 
    if (rtc.lostPower()) {
      rtcValid = false;
      log(String(F("RTC lost power!")));
    }
    log(String(F("RTC initialized.")));
  }

  // Tensosensors
  scaleL.begin(TENSO_L_DT, TENSO_L_SCK);
  scaleL.tare();

  scaleR.begin(TENSO_R_DT, TENSO_R_SCK);
  scaleR.tare();

  // Temperature sensors
  tempSensors.begin();

  log(String(F("(SYS) Found ")) + String(tempSensors.getDeviceCount(), DEC) + String(F(" temperature sensors.")));

  if (tempSensors.getAddress(insideThermometer, 0))  innerTempSensorInitialized = true;
  if (tempSensors.getAddress(outsideThermometer, 1)) outerTempSensorInitialized = true;

  if (!innerTempSensorInitialized) log(String(F("(ERROR) Unable to find address for Device 0 (Inside)")));
  if (!outerTempSensorInitialized) log(String(F("(ERROR) Unable to find address for Device 1 (Outside)")));

  tempSensors.setResolution(insideThermometer, 11);
  tempSensors.setResolution(outsideThermometer, 11);

  // Water sensors
  pinMode(WATER_SENSOR_L, INPUT_PULLUP);
  pinMode(WATER_SENSOR_H, INPUT_PULLUP);

  // Turbidity & pH sensor
  analogADC.begin();
  analogADC.setGain(GAIN_ONE);

  log(String(F("(SYS) Sensors initialized successfully.")));
}

float getGrams(HX711& scale, float scaleZero, float flaskEmpty, float flask100, bool getNetto) {
  float raw = scale.get_units(TENSO_UNITS); 
  float delta = (flask100 - flaskEmpty) / 100.0f;
  
  if (abs(delta) < 0.001f) return 0.0f;

  if (getNetto) { return (raw - flaskEmpty) / delta; }  // Netto (Only liquid)
  else { return (raw - scaleZero) / delta; }            // Brutto (Whole weight)
}
float getPH() {
  // MEDIAN SORT
  int16_t buffer[SAMPLE_SIZE];
  // Collect measures
  for (int i = 0; i < SAMPLE_SIZE; i++) {
    buffer[i] = analogADC.readADC_SingleEnded(PH_ADC_NUM);
    delay(1);
  }
  // Sort
  for (int i = 0; i < SAMPLE_SIZE - 1; i++) {
    for (int j = 0; j < SAMPLE_SIZE - i - 1; j++) {
      if (buffer[j] > buffer[j + 1]) {
        int16_t temp = buffer[j];
        buffer[j] = buffer[j + 1];
        buffer[j + 1] = temp;
      }
    }
  }
  // Median
  int16_t medianPHVal = buffer[SAMPLE_SIZE / 2];

  // Calibrate raw value
  float slope = (conf.pH7SensorVal - conf.pH10SensorVal) / 3.0f;
  if (slope == 0.0f) return 0.0f;

  float pH_value = 7.0f + (conf.pH7SensorVal - medianPHVal) / slope; 
  return pH_value;
}

void conductPHMeasure(uint32_t currentTime){
  // Calibrate
  if (currentTime - systemState.lastPHCalibrationTimestamp >= PH_CALIBRATION_RATE) {
  // pHStepper.step(stepsPerRevolution); // (ABSOLUTE ANGLE, NOT STEP)
  // calibratePHSensor(0);
  // pHStepper.step(stepsPerRevolution); // (ABSOLUTE ANGLE, NOT STEP)
  // calibratePHSensor(1);

    systemState.lastPHCalibrationTimestamp = currentTime;
    saveState(systemState);
  }
  // Measure
  // pHStepper.step(stepsPerRevolution); // (ABSOLUTE ANGLE, NOT STEP)
  environmentData.pH = getPH();
  sendPort(String(F("PH ")) + String(environmentData.pH, 2));
}

void collectEnvData() {
  // 1. Tenso data
  if (scaleL.is_ready()) { 
    environmentData.tensoL = getGrams(scaleL, conf.leftScaleZeroVal, conf.emptyLeftHarvestFlaskWeightVal, conf.ml100LeftHarvestFlaskWeightVal, false);
  } else {
    environmentData.tensoL = -1.0f;
    static uint32_t lastTensoLError = 0;
    if (millis() - lastTensoLError > 10000) {
      log(String(F("(ERROR) HX711 Left not ready.")));
      lastTensoLError = millis();
    }
  }

  if (scaleR.is_ready()) {
    environmentData.tensoR = getGrams(scaleR, conf.rightScaleZeroVal, conf.emptyRightHarvestFlaskWeightVal, conf.ml100RightHarvestFlaskWeightVal, false);
  } else {
    environmentData.tensoR = -1.0f;
    static uint32_t lastTensoRError = 0;
    if (millis() - lastTensoRError > 10000) {
      log(String(F("(ERROR) HX711 Right not ready.")));
      lastTensoRError = millis();
    }
  }

  // 2. Temperature data
  if (innerTempSensorInitialized || outerTempSensorInitialized) {
    tempSensors.requestTemperatures(); 
    
    float tIn = innerTempSensorInitialized ? tempSensors.getTempC(insideThermometer) : DEVICE_DISCONNECTED_C;
    float tOut = outerTempSensorInitialized ? tempSensors.getTempC(outsideThermometer) : DEVICE_DISCONNECTED_C;

    environmentData.tempIn = (tIn == DEVICE_DISCONNECTED_C) ? -99.9f : tIn;
    environmentData.tempOut = (tOut == DEVICE_DISCONNECTED_C) ? -99.9f : tOut;
  }

  // 3. Water level data
  uint8_t low_level = digitalRead(WATER_SENSOR_L) == HIGH ? 1 : 0;
  uint8_t high_level = digitalRead(WATER_SENSOR_H) == HIGH ? 1 : 0;

  environmentData.waterSensorsBin = (high_level << 1) | low_level;

  // 4. Turbidity data
  int turbidRaw = analogADC.readADC_SingleEnded(TURBIDITY_ADC_NUM);
  float turbidPercent = 1.0f - (turbidRaw / float(ANALOG_ADC_RESOLUTION - 1));

  environmentData.turbidity = turbidPercent;
}

// - Port Handlers -
void readPort() {
  if (!Serial.available()) return;

  // Get line
  String raw_line = Serial.readStringUntil('\n');
  raw_line.trim();

  if (raw_line.length() == 0) return;

  // Parse command
  int separator_index = raw_line.indexOf(' ');
  String cmd = String(F("")), payload = String(F(""));
  // Get payload
  if (separator_index != -1) {
    cmd = raw_line.substring(0, separator_index);
    payload = raw_line.substring(separator_index + 1);
  }
  else { cmd = raw_line; }

  // Command type reader
  switch(string_hash(cmd.c_str())){

    case string_hash("PING"): {
      pingDelay = 0;
      sendPort(String(F("PONG")));
      break;
    }
    
    case string_hash("CONFIGBRIGHTNESS"): {
      // CONFIGBRIGHTNESS X V (X - Light num 0-2; V - Value 0-255)
      int space_idx = payload.indexOf(' ');
      if (space_idx != -1) {
        uint8_t light_num = payload.substring(0, space_idx).toInt();
        uint8_t value = payload.substring(space_idx + 1).toInt();
        
        if (light_num == 0) conf.brightnessA = value;
        else if (light_num == 1) conf.brightnessB = value;
        else if (light_num == 2) conf.brightnessC = value;

        saveConfig(conf);
        sendPort(String(F("ACK")));
        
        log(String(F("(PORT) Set LED ")) + String(light_num) + String(F(" to ")) + String(value));
      }
      break;
    }
    
    case string_hash("CONFIGHARVESTPUMP"): {
      // CONFIGHARVESTPUMP V (V - Value)
      int val = payload.toInt();
      if (val >= 0 && val <= 255){
        conf.harvestPumpPower = val;
        
        saveConfig(conf);
        sendPort(String(F("ACK")));
      }
      else sendPort(String(F("NACK")));

      log(String(F("(PORT) Harvest pump power: ")) + String(conf.harvestPumpPower));
      break;
    }
    
    case string_hash("CONFIGTARGETTEMP"): {
      // CONFIGTARGETTEMP T1 T2 (T1 - Min Temp, T2 - Max Temp)
      int space_idx = payload.indexOf(' ');
      if (space_idx != -1) {
        int min = payload.substring(0, space_idx).toInt();
        int max = payload.substring(space_idx + 1).toInt();
        
        if(min <= max && min > 16 && max < 60){
          conf.minTargetTemp = min;
          conf.maxTargetTemp = max;

          saveConfig(conf);
          sendPort(String(F("ACK")));

          log(String(F("(PORT) Target Temp set. Min: ")) + String(conf.minTargetTemp) + String(F(" Max: ")) + String(conf.maxTargetTemp));
        }
        else sendPort(String(F("NACK")));
      }
      break;
    }
    
    case string_hash("CONFIGHARVESTAMOUNT"): {
      // CONFIGHARVESTAMOUNT V (V - Value g/ml)
      int val = payload.toInt();
      if(val >= 0 && val <= MAX_WATER_ML / 2){
        conf.harvestAmountMl = val;
        
        saveConfig(conf);
        sendPort(String(F("ACK")));
      }
      else sendPort(String(F("NACK")));

      log(String(F("(PORT) Harvest amount set: ")) + String(conf.harvestAmountMl));
      break;
    }
    
    case string_hash("SETLIGHTFADEDURATION"): {
      // SETLIGHTFADEDURATION V (V - Value (s))
      float val = payload.toFloat();
      if (val >= 0 && val < CONFIG_LIMIT){
        conf.lightFadeDurS = val;

        saveConfig(conf);
        sendPort(String(F("ACK")));
      }
      else sendPort(String(F("NACK")));

      log(String(F("(PORT) Light fade duration set: ")) + String(conf.lightFadeDurS));
      break;
    }
    
    case string_hash("SETLIGHTSHEDULE"): {
      // SETLIGHTSHEDULE V (V - Value (h) of light period)
      int val = payload.toInt();
      if (val >= 0 && val <= 24){
        conf.lightPeriodH = val;
        conf.darkPeriodH = 24 - val;

        saveConfig(conf);
        updateLightSchedule();
        sendPort(String(F("ACK")));
      }
      else sendPort(String(F("NACK")));

      log(String(F("(PORT) Light period hours: ")) + String(conf.lightPeriodH));
      break;
    }
    
    case string_hash("SETACTIVECOMPRESSORPERIOD"): {
      // SETACTIVECOMPRESSORPERIOD V (V - Value min)
      int val = payload.toInt();
      if (val >= 0 && val < CONFIG_LIMIT){
        conf.compressorActiveMin = val;
       
        saveConfig(conf);
        //updateCompressorSchedule();
        sendPort(String(F("ACK")));
      }
      else sendPort(String(F("NACK")));

      log(String(F("(PORT) Compressor active min: ")) + String(conf.compressorActiveMin));
      break;
    }
    
    case string_hash("SETRESTCOMPRESSORPERIOD"): {
      // SETRESTCOMPRESSORPERIOD V (V - Value min)
      int val = payload.toInt();
      if (val >= 0 && val < CONFIG_LIMIT){
        conf.compressorRestMin = val;
        
        saveConfig(conf);
        //updateCompressorSchedule();
        sendPort(String(F("ACK")));
      }
      else sendPort(String(F("NACK")));

      log(String(F("(PORT) Compressor rest min: ")) + String(conf.compressorRestMin));
      break;
    }

    case string_hash("SETPHRANGE"): {
      // SETPHRANGE X Y (X - Min, Y - Max)
      int space_idx = payload.indexOf(' ');
      if (space_idx != -1) {
        float min = payload.substring(0, space_idx).toFloat();
        float max = payload.substring(space_idx + 1).toFloat();

        if (max >= min && min > 4.0 && max < 13.0){
          conf.minPH = min;
          conf.maxPH = max;

          saveConfig(conf);
          sendPort(String(F("ACK")));

          log(String(F("(PORT) Target pH set. Min: ")) + String(conf.minPH) + String(F(" Max: ")) + String(conf.maxPH));
        }
        else sendPort(String(F("NACK")));
      }
      break;
    }

    case string_hash("DATAVALIDATED"): {
      // Blank reciever
      //sendPort(String(F("ACK")));
      break;
    }

    case string_hash("DATACORRUPTED"): {
      // Blank reciever
      //sendPort(String(F("ACK")));
      break;
    }

    case string_hash("CALIBRATESCALEZERO"): {
      calibrateFlasks(0);
      sendPort(String(F("ACK")));
      break;
    }

    case string_hash("CALIBRATEEMPTYFLASKWEIGHTVALUE"): {
      calibrateFlasks(1);
      sendPort(String(F("ACK")));
      break;
    }

    case string_hash("CALIBRATE100FLASKWEIGHTVALUE"): {
      calibrateFlasks(2);
      sendPort(String(F("ACK")));
      break;
    }

    case string_hash("REQUESTSTATE"): {
      sendEnvironment();
      sendPort(String(F("ACK")));
      break;
    }

    case string_hash("ESTOP"): {
      emergencyStop();
      sendPort(String(F("ACK")));
      break;
    }
    
    case string_hash("HARVEST"): {
      if(conf.scaleZeroValCalibrated && conf.emptyFlasksCalibrated && conf.ml100FlasksCalibrated){
        harvest();
        sendPort(String(F("ACK")));
      }
      else {
        sendPort(String(F("NACK")));
        log(String(F("(PORT) Calibrate scales first!")));
      }
      break;
    }
    
    case string_hash("ADDWATER"): {
      addWater();
      sendPort(String(F("ACK")));
      break;
    }

    default: {
      sendPort(String(F("NACK")));
      log(String(F("(PORT) Unknown command received: ")) + cmd);
      break;
    }
  }
}
void sendPort(String message) {
  if (!Serial) return; 
  Serial.println(message);
  Serial.flush(); 
}

void sendEnvironment() {
  collectEnvData();

  uint8_t compState = digitalRead(COMPRESSOR_PIN);
  uint8_t heatState = digitalRead(HEATER_PIN);
  
  String stateMsg = String(F("CURRENTSTATE ")) + 
                    String(100 * (conf.brightnessA / 255)) + String(F(" ")) + 
                    String(100 * (conf.brightnessB / 255)) + String(F(" ")) + 
                    String(100 * (conf.brightnessC / 255)) + String(F(" ")) + 
                    String(compState) + String(F(" ")) + 
                    String(heatState) + String(F(" ")) + 
                    String(100 * (conf.harvestPumpPower / 255));
  sendPort(stateMsg);

  if (outerTempSensorInitialized && innerTempSensorInitialized) { 
    sendPort(String(F("TEMP ")) + String(environmentData.tempOut, 1) + String(F(" ")) + String(environmentData.tempIn, 1)); 
  }

  sendPort(String(F("TURBIDITY ")) + String(environmentData.turbidity, 2));
  sendPort(String(F("VOLUME ")) + String(environmentData.waterSensorsBin));

  uint8_t flaskMask = 0;
  if (environmentData.tensoL >= conf.emptyLeftHarvestFlaskWeightVal) flaskMask |= 0b10;
  if (environmentData.tensoR >= conf.emptyRightHarvestFlaskWeightVal) flaskMask |= 0b01;
  int32_t weightL = (environmentData.tensoL != -1.0f) ? (int32_t)environmentData.tensoL : 0;
  int32_t weightR = (environmentData.tensoR != -1.0f) ? (int32_t)environmentData.tensoR : 0;

  sendPort(String(F("FLASKS ")) + String(flaskMask) + String(F(" ")) + String(weightL) + String(F(" ")) + String(weightR));
}

// - Software Actions -
void saveConfig(Config configToSave) {
  EEPROM.put(0, configToSave);
  log(String(F("(SYS) Config saved to Flash EEPROM.")));
}
void saveState(SystemState stateToSave) {
  int stateAddress = sizeof(Config);
  EEPROM.put(stateAddress, stateToSave);
  // log(String(F("(SYS) State saved to EEPROM.")));
}
Config loadConfig() {
  Config loadedConfig;
  EEPROM.get(0, loadedConfig);

  if (loadedConfig.lightPeriodH > 24 || loadedConfig.maxTargetTemp <= 0 || loadedConfig.maxTargetTemp > 100) {
    log(String(F("(SYS) Config EEPROM is empty or corrupted! Loading hardcoded defaults...")));
    Config defaultRelease;
    return defaultRelease; 
  }

  log(String(F("(SYS) Config successfully loaded from Flash EEPROM.")));
  return loadedConfig;
}
SystemState loadState() {
  SystemState loadedState;
  int stateAddress = sizeof(Config);
  EEPROM.get(stateAddress, loadedState);

  if (loadedState.validSignature != 0xA11C001) {
    log(String(F("(SYS) State EEPROM is empty or corrupted! Initializing clean state...")));
    SystemState defaultState;
    return defaultState;
  }

  log(String(F("(SYS) State successfully loaded from EEPROM.")));
  return loadedState;
}

void log(String msg) { sendPort(String(F("LOG ")) + msg); }

void updateLightSchedule() {
  uint32_t currentTime = rtc.now().unixtime();
  
  uint32_t currentPeriodS = systemState.light ? (uint32_t)conf.lightPeriodH * 3600 : (uint32_t)conf.darkPeriodH * 3600;
  systemState.plannedLightSwitchTimestamp = currentTime + currentPeriodS;
  
  saveState(systemState);
  log(String(F("(SYS) Light schedule updated on the fly.")));
}
void updateCompressorSchedule() {
  /* Just change config (future changes) [NOW WE DON'T NEED THIS FUNCTION] */ 
  saveState(systemState);
}

void calibrateFlasks(uint8_t mode) {
  float sl = scaleL.get_units(TENSO_UNITS);
  float sr = scaleR.get_units(TENSO_UNITS);
  if (mode == 0) {        // Remember zero
    conf.leftScaleZeroVal = sl;
    conf.rightScaleZeroVal = sr;
    conf.scaleZeroValCalibrated = true;
  }
  else if (mode == 1) {   // Empty flasks weight
    conf.emptyLeftHarvestFlaskWeightVal = sl;
    conf.emptyRightHarvestFlaskWeightVal = sr;
    conf.emptyFlasksCalibrated = true;
  }
  else {                  // 100 ml flasks
    conf.ml100LeftHarvestFlaskWeightVal = sl;
    conf.ml100RightHarvestFlaskWeightVal = sr;
    conf.ml100FlasksCalibrated = true;
  }
  saveConfig(conf);
}
void calibratePHSensor(uint8_t mode){
  int16_t pHVal = analogADC.readADC_SingleEnded(PH_ADC_NUM);
  if (mode == 0) {
    conf.pH7SensorVal = pHVal;
    conf.normPHCalibrated = true;
  }
  else {
    conf.pH10SensorVal = pHVal;
    conf.highPHCalibrated = true;
  }
  saveConfig(conf);
}

// - Physical Actions - 
// Handlers
void lightCycleHandler() {
  int state = systemState.light ? 1 : 0;
  int stateInv = 1 - state;
  if (switching) {
    float elapsedTime = (millis() - startSwitchTime) / 1000.0;
    float x = (elapsedTime / (conf.lightFadeDurS + 0.0001));

    float targetValPerc = abs(stateInv - x);

    analogWrite(LED_A_PIN, targetValPerc * conf.brightnessA);
    analogWrite(LED_B_PIN, targetValPerc * conf.brightnessB);
    analogWrite(LED_C_PIN, targetValPerc * conf.brightnessC);

    if (x >= 1.0) {
      x = 1.0;
      switching = false;
      log(String(F("(SYS) Light switched. Now: ")) + String(systemState.light ? "ON" : "OFF"));
    }
  }
}
void carbonizingCycleHandler(uint32_t currentTimestamp) {
  if (currentTimestamp >= systemState.plannedCompressorSwitchTimestamp) {
    uint32_t timer = systemState.carbonizing ? conf.compressorRestMin * 60 : conf.compressorActiveMin * 60;
    systemState.plannedCompressorSwitchTimestamp = currentTimestamp + timer;
    
    systemState.carbonizing = !systemState.carbonizing;
    digitalWrite(COMPRESSOR_PIN, systemState.carbonizing ? HIGH : LOW);

    saveState(systemState);

    log(String(F("(SYS) Compressor switched. New state: ")) + String(systemState.carbonizing) + String(F(". Next switch in (s): ")) + String(timer));
  }
}
void tempWatcher(){
  if (environmentData.tempIn < conf.minTargetTemp) { analogWrite(HEATER_PIN, HIGH); }
  else { analogWrite(HEATER_PIN, LOW); }

  if(environmentData.tempIn > conf.maxTargetTemp) { analogWrite(HEATER_PIN, LOW); }
}
void waterLevelWatcher() {
  if (isWaterFlow) {
    if(digitalRead(WATER_SENSOR_H) || millis() - startWaterFlowTimestamp >= 60000) {
      digitalWrite(WATER_PUMP, LOW);
      sendPort(F("COMPLETED"));
      isWaterFlow = false;
    }
  }
}
void harvestHandler() {
  if (harvestPumpActive) {
    float liquidL = getGrams(scaleL, conf.leftScaleZeroVal, conf.emptyLeftHarvestFlaskWeightVal, conf.ml100LeftHarvestFlaskWeightVal, true);
    float liquidR = getGrams(scaleR, conf.rightScaleZeroVal, conf.emptyRightHarvestFlaskWeightVal, conf.ml100RightHarvestFlaskWeightVal, true);
    
    if (liquidL >= conf.harvestAmountMl && liquidR >= conf.harvestAmountMl) {
      analogWrite(PUMP_PIN, 0);
      harvestPumpActive = false;
      sendPort(F("HARVESTLOG ") + String(2 * harvestAmountMl) + " " + String(environmentData.turbidity));
      sendPort(F("COMPLETED"));
      log(String(F("(SYS) Harvest done.")));
    }
  }
}

// Actions
void switchLight() {
  startSwitchTime = millis();
  switching = true;
  log(String(F("(SYS) Light switching...")));
}
void harvest() {
  log(String(F("(SYS) Harvest started.")));
  analogWrite(PUMP_PIN, conf.harvestPumpPower);
  harvestPumpActive = true;
}
void addWater() {
  digitalWrite(WATER_PUMP, HIGH);
  startWaterFlowTimestamp = millis();
  isWaterFlow = true;
}
void emergencyStop() {
  digitalWrite(LED_A_PIN, LOW);
  digitalWrite(LED_B_PIN, LOW);
  digitalWrite(LED_C_PIN, LOW);

  digitalWrite(PUMP_PIN, LOW);

  digitalWrite(HEATER_PIN, LOW);
  digitalWrite(COMPRESSOR_PIN, LOW);

  digitalWrite(WATER_PUMP, LOW);

  sendPort(F("COMPLETED"));
}

// ========= MAIN CODE ========= //
void setup() {
  Serial.begin(SERIAL_BAUDRATE);

  conf = loadConfig();
  systemState = loadState();

  initSensors();

  pinMode(LED_A_PIN, OUTPUT);
  pinMode(LED_B_PIN, OUTPUT);
  pinMode(LED_C_PIN, OUTPUT);

  pinMode(PUMP_PIN, OUTPUT);

  pinMode(HEATER_PIN, OUTPUT);
  pinMode(COMPRESSOR_PIN, OUTPUT);

  pinMode(WATER_PUMP, OUTPUT);

  emergencyStop();

  if (systemState.light){
    analogWrite(LED_A_PIN, conf.brightnessA);
    analogWrite(LED_B_PIN, conf.brightnessB);
    analogWrite(LED_C_PIN, conf.brightnessC);
  }

  if (systemState.carbonizing){
    digitalWrite(COMPRESSOR_PIN, HIGH);
  }
}

void loop() {
  uint32_t currentTime = rtc.now().unixtime();
  readPort();

  // Ping counter
  if (millis() - lastPingCheck >= 1000) {
    pingDelay += 1.0f;
    lastPingCheck = millis();
    is_connected = !(pingDelay > 30.0f);
  }

  // Environment updater
  if(millis() - lastEnvUpdated >= 5 * 1000){
    collectEnvData();
    lastEnvUpdated = millis();
  }

  // Light handler
  lightCycleHandler();
  if (currentTime >= systemState.plannedLightSwitchTimestamp) {
    systemState.light = !systemState.light;
    switchLight();

    uint32_t newPlannedS = systemState.light ? (uint32_t)conf.lightPeriodH * 3600 : (uint32_t)conf.darkPeriodH * 3600;
    systemState.plannedLightSwitchTimestamp = currentTime + newPlannedS;

    saveState(systemState);
  }

  // Carbonizing handler
  carbonizingCycleHandler(currentTime);

  // pH data Collector
  if (currentTime >= systemState.plannedPHMeasure){
    conductPHMeasure(currentTime);

    systemState.plannedPHMeasure = currentTime + 6U * 3600U;
    saveState(systemState);
  }

  // Temperature watcher
  tempWatcher();

  // Water level watcher
  waterLevelWatcher();

  // Harvest handler
  harvestHandler();
}