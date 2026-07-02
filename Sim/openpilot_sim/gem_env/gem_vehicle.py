#!/usr/bin/env python3
"""
GEM E4 vehicle for MetaDrive — kinematically matches the real cart.

MetaDrive sets vehicle geometry/dynamics via CLASS CONSTANTS on a vehicle subclass
(the env `vehicle_config` dict does NOT override them). Values sourced from
Hardware/cart_parameters.md (canonical: cart_parameters.xacro).

Reused by both the Mac standalone tests and the Openpilot tools/sim bridge.
"""
from metadrive.component.vehicle.vehicle_type import DefaultVehicle


class GemE4Vehicle(DefaultVehicle):
    # --- geometry (GEM E4) ---
    # wheelbase 1.83 m, split ~evenly about the CG (front/rear axle to CG)
    FRONT_WHEELBASE = 0.915
    REAR_WHEELBASE = 0.915
    LATERAL_TIRE_TO_CENTER = 0.635          # track width 1.27 m / 2
    TIRE_RADIUS = 0.305                      # 24.5" tire / 2
    TIRE_WIDTH = 0.22

    # --- mass / dynamics ---
    MASS = 709                               # curb weight kg

    # --- steering ---
    MAX_STEERING = 28.0                      # road-wheel max angle (deg), stock GEM

    # low-speed vehicle: stock cap ~25 mph. Phase-1 real cart is governed to 5 mph,
    # but leave headroom here so the model isn't speed-starved during the drive test.
    @property
    def max_speed_km_h(self):
        return 40.0                          # ~25 mph

    @property
    def max_speed_m_s(self):
        return 40.0 / 3.6


# name used to select this vehicle via vehicle_config["vehicle_model"]
GEM_E4_VEHICLE_NAME = "gem_e4"


def register_gem_vehicle(name: str = GEM_E4_VEHICLE_NAME):
    """Register GemE4Vehicle in MetaDrive's forward (name->class) AND reverse
    (class->name) type maps. Both are required: agent_manager looks up the class
    by name, and BaseVehicle.reset() looks the name back up by class."""
    import metadrive.component.vehicle.vehicle_type as vt
    vt.vehicle_type[name] = GemE4Vehicle
    vt.vehicle_class_to_type[GemE4Vehicle] = name
    return name


def wheelbase(cls=GemE4Vehicle) -> float:
    return cls.FRONT_WHEELBASE + cls.REAR_WHEELBASE
