#pragma once

// === PINOUT === //
// Sensors
#define TEMP_SENSOR_PIN     PA0   // OneWire
#define PH_SENSOR_PIN       PA1   // ADC1_IN1 (analog, <= 3.3V)
#define TURB_SENSOR_PIN     PA2   // ADC1_IN2 (analog, <= 3.3V)
#define WL_SENSOR_PIN       PA3   // Digital sensor

// I2C (DS3231 RTC)
#define I2C_SDA_PIN         PB7   // Wire SDA
#define I2C_SCL_PIN         PB6   // Wire SCL

// PWM outputs
#define HEATER_MOS_PIN      PA6   // TIM3_CH1 (PWM to heater MOSFET gate)
#define LB_PIN              PA7   // TIM3_CH2 (Bottom light PWM)
#define LS_PIN              PB0   // TIM3_CH3 (Side light PWM)
#define LU_PIN              PB1   // TIM3_CH4 (Upper light PWM)

// TB6612FNG motor driver
#define TB6612_PWMA_PIN     PA8   // TIM1_CH1 (PWM)
#define TB6612_AIN1_PIN     PB12
#define TB6612_AIN2_PIN     PB13
#define TB6612_PWMB_PIN     PA9   // TIM1_CH2 (PWM)
#define TB6612_BIN1_PIN     PB14
#define TB6612_BIN2_PIN     PB15
#define TB6612_STBY_PIN     PB10

// 28BYJ-48 Stepper (4 control lines)
#define STEPPER_IN1_PIN     PC13
#define STEPPER_IN2_PIN     PC14
#define STEPPER_IN3_PIN     PC15
#define STEPPER_IN4_PIN     PB3

// Servo
#define SERVO_PIN           PA10  // TIM1_CH3 (сигнал сервопривода)

// Optional / future pH dosing pump
#define PH_MOTOR_PIN        PB4   // Digital / PWM

// CONFIGURATION //
#define HEATER_POWER    12 * 4
#define TEMP_INADVANCE  3

#define BAUDRATE        115200
#define PWM_MAX_DUTY    255U

#define THIRTY_MIN_INTERVAL_MS  (30UL * 60UL * 1000UL)
#define TWELVE_HOUR_INTERVAL_MS (12UL * 60UL * 60UL * 1000UL)

#define MEDIAN_MAX_SAMPLES      31