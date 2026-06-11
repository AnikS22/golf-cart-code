/*
 * kartech_brake.h — J1939 driver for the Kartech 1A001HAJ linear actuator.
 *
 * Header-only, templated on the FlexCAN_T4 bus type so the caller declares
 * the CAN module:
 *
 *     FlexCAN_T4<CAN3, RX_SIZE_256, TX_SIZE_16> kartech_can;
 *     kartech_can.begin();
 *     kartech_can.setBaudRate(VEHICLE_J1939_BITRATE_HZ);   // 250 kbps
 *     ...
 *     kartech::brake_full(kartech_can);
 *
 * Bus must be a 250 kbps J1939 segment DEDICATED to the Kartech.
 * Do NOT share this bus with the GEM internal J1939 (TX-forbidden zone).
 *
 * PROTOCOL (reverse-engineered by FAU MPCR 2020 team; preserved bit-for-bit):
 *   - Priority    = 0
 *   - PGN         = 65280 (0xFF00, Manufacturer Proprietary A, PDU2 broadcast)
 *   - Source addr = 128
 *   - 29-bit CAN ID = (0 << 26) | (0xFF << 16) | (0x00 << 8) | 0x80 = 0x00FF0080
 *   - Payload     = { 0x0F, 0x4A, b2, b3, 0, 0, 0, 0 }
 *                   where (b2, b3) selects the command (see captured table).
 *
 * Captured command table (2020 BrakeDuino, src in kartech_brake_reference/):
 *   clutch_on        (196, 137)  — engage actuator drive
 *   clutch_off       (208,   7)  — disengage
 *   extend_3in       ( 91, 204)  — extend ~3 inches
 *   retract          (238, 195)  — retract
 *   brake_full       (193, 203)  — full brake position
 *   brake_light      (105, 204)  — brake light trigger
 *   release_to_stock (192, 205)  — return to stock / zero
 *
 * PARAMETERIZED POSITION (CONTINUOUS CONTROL):
 *   send_position_14bit(pos) writes any 14-bit Kartech position. The encoding
 *   is reverse-engineered from the 2020 captures:
 *       byte2 = pos & 0xFF                       (low 8 bits)
 *       byte3 = ((pos >> 8) & 0x3F) | 0xC0       (high 6 bits + magic "11")
 *   send_demand_byte(demand_0_255) mirrors the 2020 RPi-Serial API exactly:
 *       position = demand * 40
 *
 * OBSERVED POSITION CONSTANTS (from the captured frames):
 *   POS_FULL_BRAKE    = 3009  ← brake_full frame
 *   POS_EXTEND_3IN    = 3163  ← extend_3in frame
 *   POS_RELEASE_STOCK = 3520  ← release_to_stock frame
 *   Higher position = actuator more EXTENDED = LESS brake. Lower = more brake.
 *   Useful braking band is roughly 3000–3520 (~510 units of travel).
 *
 * NOT YET PORTED:
 *   - Feedback PGNs. Kartech echoes position/status on some PGN we have not
 *     yet sniffed. Add an onReceive handler once captured.
 */

#ifndef KARTECH_BRAKE_H
#define KARTECH_BRAKE_H

#include <stdint.h>
#include <FlexCAN_T4.h>

namespace kartech {

constexpr uint32_t TX_ID         = 0x00FF0080U;  /* pri=0, PGN=0xFF00, SA=128 */
constexpr uint8_t  HEADER_BYTE_0 = 0x0F;
constexpr uint8_t  HEADER_BYTE_1 = 0x4A;

/* Observed Kartech position constants (14-bit, derived from captured frames).
 * Higher value = actuator more extended = LESS brake. */
constexpr uint16_t POS_FULL_BRAKE    = 3009;
constexpr uint16_t POS_EXTEND_3IN    = 3163;
constexpr uint16_t POS_RELEASE_STOCK = 3520;

template <typename Bus>
inline void send_raw(Bus& bus, uint8_t b2, uint8_t b3) {
    CAN_message_t f{};
    f.id              = TX_ID;
    f.flags.extended  = 1;     /* J1939 = 29-bit IDs */
    f.len             = 8;
    f.buf[0] = HEADER_BYTE_0;
    f.buf[1] = HEADER_BYTE_1;
    f.buf[2] = b2;
    f.buf[3] = b3;
    /* buf[4..7] are zero-initialised by CAN_message_t{} */
    bus.write(f);
}

/* Captured 2020-team frames (bit-for-bit; known-good against 1A001HAJ). */
template <typename Bus> inline void clutch_on(Bus& b)        { send_raw(b, 196, 137); }
template <typename Bus> inline void clutch_off(Bus& b)       { send_raw(b, 208,   7); }
template <typename Bus> inline void extend_3in(Bus& b)       { send_raw(b,  91, 204); }
template <typename Bus> inline void retract(Bus& b)          { send_raw(b, 238, 195); }
template <typename Bus> inline void brake_full(Bus& b)       { send_raw(b, 193, 203); }
template <typename Bus> inline void brake_light(Bus& b)      { send_raw(b, 105, 204); }
template <typename Bus> inline void release_to_stock(Bus& b) { send_raw(b, 192, 205); }

/* Parameterized position — continuous control. */
template <typename Bus>
inline void send_position_14bit(Bus& bus, uint16_t pos_14bit) {
    if (pos_14bit > 0x3FFFu) pos_14bit = 0x3FFFu;
    const uint8_t lsb = (uint8_t)(pos_14bit & 0xFFu);
    const uint8_t msb = (uint8_t)(((pos_14bit >> 8) & 0x3Fu) | 0xC0u);
    send_raw(bus, lsb, msb);
}

/* 2020-API equivalent: brake demand byte 0..255. position = demand * 40. */
template <typename Bus>
inline void send_demand_byte(Bus& bus, uint8_t demand_0_255) {
    send_position_14bit(bus, (uint16_t)demand_0_255 * 40u);
}

/* Continuous brake force command: 0 = released, 1000 = full brake.
 * Linearly interpolates inside the observed useful band
 * [POS_RELEASE_STOCK .. POS_FULL_BRAKE]. */ 
template <typename Bus>
inline void send_brake_permil(Bus& bus, uint16_t brake_permil) {
    if (brake_permil > 1000u) brake_permil = 1000u;
    const int32_t span = (int32_t)POS_FULL_BRAKE - (int32_t)POS_RELEASE_STOCK;  /* negative */
    const int32_t pos  = (int32_t)POS_RELEASE_STOCK + (span * (int32_t)brake_permil) / 1000;
    send_position_14bit(bus, (uint16_t)pos);
}

}  /* namespace kartech */

#endif /* KARTECH_BRAKE_H */
