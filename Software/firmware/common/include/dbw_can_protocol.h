/*
 * dbw_can_protocol.h — Canonical CAN protocol for the GEM E4 drive-by-wire bus.
 *
 * Compiles as plain C99 on Teensy (Arduino-Teensy core via PlatformIO) and as
 * C++ on the Jetson side (gem_dbw_bridge ROS 2 node). Header-only; no .c.
 *
 * RULES OF THE BUS:
 *   - 500 kbps, 11-bit IDs, little-endian multi-byte fields.
 *   - All payload structs are exactly 8 bytes (the CAN classic data length).
 *     Use memcpy(struct, frame.data, 8) on RX and the inverse on TX.
 *   - The DBW bus is ISOLATED from the EPAS bus and the GEM J1939 bus.
 *     Motion Teensy bridges DBW <-> EPAS in firmware (not physically).
 *
 * SAFETY:
 *   - master_state is sticky FAULT until key cycle.
 *   - Watchdog: Jetson HB lost >100 ms → throttle 0, steering coast, master FAULT.
 */

#ifndef DBW_CAN_PROTOCOL_H
#define DBW_CAN_PROTOCOL_H

#include <stdint.h>

#ifdef __cplusplus
extern "C" {
#endif

/* ============================================================================
 * Bus parameters
 * ========================================================================= */
#define DBW_BUS_BITRATE_HZ      500000U
#define EPAS_BUS_BITRATE_HZ     250000U   /* MEASURED on the cart 2026-07-10 by
                                           sweeping CAN2 receive-only: 250k is
                                           the only rate that decodes frames
                                           (0x290+0x292, REC=0, ERROR_ACTIVE).
                                           500k and 1M both give zero RX with
                                           REC pinned ~130 — that is a bitrate
                                           mismatch, not the wiring fault the
                                           old comment here claimed. */
#define VEHICLE_J1939_BITRATE_HZ 250000U  /* SAE J1939-11 standard */

/* ============================================================================
 * CAN IDs — DBW BUS (between Jetson, Motion Teensy, Pedals Teensy)
 * ========================================================================= */
#define ID_JETSON_HEARTBEAT     0x100U  /* Jetson -> MCUs, 50 ms */
#define ID_STEER_CMD            0x110U  /* Jetson -> Motion, 20 ms */
#define ID_STEER_STATUS         0x111U  /* Motion -> bus,    20 ms */
#define ID_STEER_TORQUE_RAW     0x112U  /* Motion -> bus,    20 ms */
#define ID_THROTTLE_CMD         0x120U  /* Jetson -> Pedals, 20 ms */
#define ID_THROTTLE_STATUS      0x121U  /* Pedals -> bus,    20 ms */
#define ID_BRAKE_CMD            0x130U  /* Jetson -> Pedals, 20 ms */
#define ID_BRAKE_STATUS         0x131U  /* Pedals -> bus,    20 ms */
#define ID_ESTOP_STATE          0x140U  /* Pedals -> bus,    50 ms */
#define ID_MCU_HB_MOTION        0x150U  /* Motion -> bus,    50 ms */
#define ID_MCU_HB_PEDALS        0x151U  /* Pedals -> bus,    50 ms */
#define ID_VEHICLE_STATE        0x160U  /* Pedals -> bus,    50 ms (J1939 decoded) */

/* ============================================================================
 * CAN IDs — EPAS BUS (DCE Motorsport fixed protocol)
 *
 * The EPAS18 Ultra ECU on this cart accepts msg #3 on ID 0x298 (NOT the 0x296
 * printed in the DCE manual) at 50–200 Hz; 200 ms timeout reverts to local
 * power-assist. VERIFIED ON HARDWARE 2026-07-10: commanding 0x298 {map,torque,
 * 0..} made selected_map echo, the remote bit set, and the column motor turn
 * (duty/current/angle all responded). 0x296 was silently ignored — ACK'd at the
 * CAN bit level but dropped by the ECU's ID filter, which looked like "standard
 * firmware / no autonomous variant." It is NOT: the autonomous firmware is
 * present; the manual's msg#3 ID is just wrong for this unit. Frame is {D0=map
 * 0/1, D1=torque 128=center, D2..=0}; the mirror byte the manual describes is
 * NOT required here. See reference_epas18_ultra.md and Old_code/steering.
 * ========================================================================= */
#define ID_EPAS_MSG1            0x290U  /* EPAS -> bus, 100 ms (torque/duty/I/V/temp + raw torque A/B) */
#define ID_EPAS_MSG2            0x292U  /* EPAS -> bus, 100 ms (angle/map/error/status/limits) */
#define ID_EPAS_MSG3            0x298U  /* bus -> EPAS, 50–200 Hz (map + torque demand). 0x298 verified on
                                           hardware 2026-07-10; manual's 0x296 is ignored by this ECU. */

/* ============================================================================
 * Periods (ms)
 * ========================================================================= */
#define PERIOD_HEARTBEAT_MS     50U
#define PERIOD_CMD_MS           20U
#define PERIOD_STATUS_MS        20U
#define PERIOD_ESTOP_MS         50U
#define PERIOD_VEHICLE_MS       50U
#define PERIOD_EPAS_TX_MS       5U      /* 200 Hz */
#define WATCHDOG_TIMEOUT_MS     100U    /* HB-lost trigger */

/* ============================================================================
 * Master state machine
 * ========================================================================= */
typedef enum {
    MASTER_STATE_DISENGAGED = 0,
    MASTER_STATE_ARMED      = 1,
    MASTER_STATE_ACTIVE     = 2,
    MASTER_STATE_FAULT      = 3,
} master_state_t;

/* ============================================================================
 * Fault flags (bitfield, used by every *_STATUS frame's fault_flags byte)
 * ========================================================================= */
#define FAULT_OVERCURRENT       (1U << 0)
#define FAULT_ENCODER_SENSOR    (1U << 1)
#define FAULT_PLAUSIBILITY      (1U << 2)
#define FAULT_WATCHDOG          (1U << 3)
#define FAULT_RANGE_LIMIT       (1U << 4)
#define FAULT_DRIVER_OVERRIDE   (1U << 5)
#define FAULT_HW_ESTOP          (1U << 6)
#define FAULT_EPAS_FAULT        (1U << 7)

/* ============================================================================
 * Vehicle gear (decoded from J1939 PGN 61445 byte 6, see reference_gem_e4_j1939_pgns.md)
 * ========================================================================= */
typedef enum {
    GEAR_NEUTRAL  = 0,
    GEAR_FORWARD  = 1,
    GEAR_REVERSE  = 2,
    GEAR_CHARGING = 3,
} vehicle_gear_t;

/* ============================================================================
 * Payload structs — every struct is exactly 8 bytes
 * ========================================================================= */

typedef struct __attribute__((packed)) {
    uint32_t counter;        /* monotonic, wraps */
    uint8_t  state;          /* master_state_t */
    uint8_t  reserved;
    uint16_t crc;            /* CRC-16 over preceding 6 bytes (poly 0x1021, init 0xFFFF) */
} jetson_heartbeat_t;

typedef struct __attribute__((packed)) {
    int16_t  angle_centideg;       /* commanded steering wheel angle, hundredths of a degree */
    uint16_t max_rate_centideg_s;  /* slew limiter, hundredths/sec */
    uint8_t  enable;               /* 1 = autonomous control active */
    uint8_t  reserved[3];
} steer_cmd_t;

typedef struct __attribute__((packed)) {
    int16_t  angle_centideg;       /* measured steering wheel angle */
    int16_t  motor_current_mA;
    uint8_t  fault_flags;
    uint8_t  epas_state;           /* 0=local, 1=remote-active, 2=remote-faulted */
    uint16_t epas_error_code;      /* EPAS18 msg #2 D4 (e.g. 100=low V, 102=torque sensor) */
} steer_status_t;

typedef struct __attribute__((packed)) {
    uint8_t  torque_a_raw;         /* EPAS msg #1 D6 — monitor for manual override */
    uint8_t  torque_b_raw;         /* EPAS msg #1 D7 */
    uint8_t  epas_status_flags;    /* EPAS msg #2 D6 */
    uint8_t  epas_limit_flags;     /* EPAS msg #2 D7 */
    uint8_t  reserved[4];
} steer_torque_raw_t;

typedef struct __attribute__((packed)) {
    uint16_t throttle_permil;      /* 0–1000 */
    uint8_t  enable;
    uint8_t  reserved[5];
} throttle_cmd_t;

typedef struct __attribute__((packed)) {
    uint16_t dac1_mV;
    uint16_t dac2_mV;
    uint8_t  relay_state;          /* 0=pedal, 1=DAC */
    uint8_t  fault_flags;
    uint8_t  reserved[2];
} throttle_status_t;

typedef struct __attribute__((packed)) {
    uint16_t brake_permil;         /* 0–1000 */
    uint8_t  enable;
    uint8_t  reserved[5];
} brake_cmd_t;

typedef struct __attribute__((packed)) {
    uint16_t actuator_pos_mm_x10;  /* tenths of mm */
    uint16_t actuator_current_mA;
    uint8_t  fault_flags;
    uint8_t  reserved[3];
} brake_status_t;

typedef struct __attribute__((packed)) {
    uint8_t  estop_loop;           /* 1 = loop closed (OK) */
    uint8_t  brake_pedal;          /* 1 = pressed */
    uint8_t  wheel_torque_override;/* 1 = driver fighting wheel */
    uint8_t  dash_switch;          /* bit0 ARM, bit1 ENGAGE, bit2 DISENGAGE */
    uint8_t  master_state;         /* master_state_t */
    uint8_t  reserved[3];
} estop_state_t;

typedef struct __attribute__((packed)) {
    uint32_t counter;
    uint8_t  state;                /* master_state_t */
    uint8_t  reserved[3];
} mcu_heartbeat_t;

typedef struct __attribute__((packed)) {
    uint16_t speed_mph_x100;       /* hundredths of mph (e.g. 5.0 mph = 500) */
    uint8_t  gear;                 /* vehicle_gear_t */
    uint16_t traction_voltage_x10; /* tenths of V */
    uint8_t  j1939_link_state;     /* 0=down, 1=up, 2=stale */
    uint8_t  reserved[2];
} vehicle_state_t;

/* ============================================================================
 * EPAS18 Ultra payload structs (DCE Motorsport protocol, separate bus)
 * ========================================================================= */

typedef struct __attribute__((packed)) {
    uint8_t torque_processed;      /* D0: signed */
    uint8_t motor_duty_pct;        /* D1 */
    uint8_t current_A;             /* D2 */
    uint8_t supply_voltage_x10;    /* D3: 1 LSB = 100 mV */
    uint8_t switch_position;       /* D4: 0–15 */
    uint8_t box_temperature_C;     /* D5 */
    uint8_t torque_a_raw;          /* D6: monitor for override */
    uint8_t torque_b_raw;          /* D7: monitor for override */
} epas_msg1_t;

typedef struct __attribute__((packed)) {
    uint8_t steering_angle;        /* D0 */
    uint8_t analog_ch1;            /* D1 */
    uint8_t analog_ch2;            /* D2 */
    uint8_t selected_map;          /* D3: 0–5 */
    uint8_t error_code;            /* D4: 100=low V, 101=tq not connected, 102=tq fault, 103=I sensor, 104=motor pwr, 105=motor not connected, 106=motor stalled, 109=overcurrent, 110=overtemp, 111=internal */
    uint8_t digital_io;            /* D5 */
    uint8_t status_flags;          /* D6: b0 paused, b1 motor fwd, b2 motor rev, b3 host_mode_active, b4 fault_light */
    uint8_t limit_flags;           /* D7: b0 LH stop, b1 RH stop, b2 overtemp, b7 remote_mode_active */
} epas_msg2_t;

#define EPAS_STATUS_HOST_MODE_ACTIVE    (1U << 3)
#define EPAS_LIMIT_REMOTE_MODE_ACTIVE   (1U << 7)

typedef struct __attribute__((packed)) {
    uint8_t map;                   /* D0: 0=local, 1–5=autonomous map (higher=faster response) */
    uint8_t torque_a;              /* D1: 128=zero, range 64–192 */
    uint8_t torque_b;              /* D2: 255 - torque_a (mirror) */
    uint8_t reserved[5];
} epas_msg3_t;

/* Helper: build epas_msg3_t from a signed torque demand (-64..+64).
 * Positive torque_demand = right turn. Choose map per response speed:
 *   1 = gentle, 5 = aggressive. Start with 2-3 for smooth driving. */
static inline epas_msg3_t epas_make_demand(uint8_t map_1to5, int8_t torque_demand) {
    epas_msg3_t m = {0};
    if (torque_demand > 64)  torque_demand = 64;
    if (torque_demand < -64) torque_demand = -64;
    m.map      = map_1to5;
    m.torque_a = (uint8_t)(128 + torque_demand);
    m.torque_b = (uint8_t)(255 - m.torque_a);
    return m;
}

/* Helper: detect manual override.
 * Pass two consecutive raw torque readings (50 ms apart) and a baseline.
 * Returns nonzero if driver is fighting the wheel.
 * Tune SPIKE_THRESHOLD on the bench. */
#define MANUAL_OVERRIDE_SPIKE_BITS 8
static inline int epas_manual_override_detected(
    uint8_t torque_a_now, uint8_t torque_b_now,
    uint8_t torque_a_baseline, uint8_t torque_b_baseline)
{
    int da = (int)torque_a_now - (int)torque_a_baseline;
    int db = (int)torque_b_now - (int)torque_b_baseline;
    if (da <  0) da = -da;
    if (db <  0) db = -db;
    return (da > MANUAL_OVERRIDE_SPIKE_BITS) || (db > MANUAL_OVERRIDE_SPIKE_BITS);
}

/* ============================================================================
 * Compile-time payload-size assertions (catch struct-padding bugs early)
 * ========================================================================= */
#ifdef __cplusplus
static_assert(sizeof(jetson_heartbeat_t) == 8, "jetson_heartbeat_t must be 8B");
static_assert(sizeof(steer_cmd_t)        == 8, "steer_cmd_t must be 8B");
static_assert(sizeof(steer_status_t)     == 8, "steer_status_t must be 8B");
static_assert(sizeof(steer_torque_raw_t) == 8, "steer_torque_raw_t must be 8B");
static_assert(sizeof(throttle_cmd_t)     == 8, "throttle_cmd_t must be 8B");
static_assert(sizeof(throttle_status_t)  == 8, "throttle_status_t must be 8B");
static_assert(sizeof(brake_cmd_t)        == 8, "brake_cmd_t must be 8B");
static_assert(sizeof(brake_status_t)     == 8, "brake_status_t must be 8B");
static_assert(sizeof(estop_state_t)      == 8, "estop_state_t must be 8B");
static_assert(sizeof(mcu_heartbeat_t)    == 8, "mcu_heartbeat_t must be 8B");
static_assert(sizeof(vehicle_state_t)    == 8, "vehicle_state_t must be 8B");
static_assert(sizeof(epas_msg1_t)        == 8, "epas_msg1_t must be 8B");
static_assert(sizeof(epas_msg2_t)        == 8, "epas_msg2_t must be 8B");
static_assert(sizeof(epas_msg3_t)        == 8, "epas_msg3_t must be 8B");
#else
_Static_assert(sizeof(jetson_heartbeat_t) == 8, "jetson_heartbeat_t must be 8B");
_Static_assert(sizeof(steer_cmd_t)        == 8, "steer_cmd_t must be 8B");
_Static_assert(sizeof(steer_status_t)     == 8, "steer_status_t must be 8B");
_Static_assert(sizeof(steer_torque_raw_t) == 8, "steer_torque_raw_t must be 8B");
_Static_assert(sizeof(throttle_cmd_t)     == 8, "throttle_cmd_t must be 8B");
_Static_assert(sizeof(throttle_status_t)  == 8, "throttle_status_t must be 8B");
_Static_assert(sizeof(brake_cmd_t)        == 8, "brake_cmd_t must be 8B");
_Static_assert(sizeof(brake_status_t)     == 8, "brake_status_t must be 8B");
_Static_assert(sizeof(estop_state_t)      == 8, "estop_state_t must be 8B");
_Static_assert(sizeof(mcu_heartbeat_t)    == 8, "mcu_heartbeat_t must be 8B");
_Static_assert(sizeof(vehicle_state_t)    == 8, "vehicle_state_t must be 8B");
_Static_assert(sizeof(epas_msg1_t)        == 8, "epas_msg1_t must be 8B");
_Static_assert(sizeof(epas_msg2_t)        == 8, "epas_msg2_t must be 8B");
_Static_assert(sizeof(epas_msg3_t)        == 8, "epas_msg3_t must be 8B");
#endif

#ifdef __cplusplus
}
#endif

#endif /* DBW_CAN_PROTOCOL_H */
