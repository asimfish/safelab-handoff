"""Versioned callback32 clock oracle; never rewrites simulator or recorded data.

The nominal 120 Hz field and original tolerances are retained. PhysX supplies
float32 callback durations to Isaac's double current_time accumulator. Recorder
continues to subtract the nominal initial tick offset exactly as before.
"""
import math
import struct

VERSION = 'native_callback32_clock_v60'
NOMINAL_DT = 1 / 120
CALLBACK32_DT = struct.unpack('<f', struct.pack('<f', NOMINAL_DT))[0]
NOMINAL_TOLERANCE = 1e-8
ACTUAL_TOLERANCE = 1e-5


def require(condition, reason):
    if not condition:
        raise ValueError(reason)


def finite_time(value):
    return type(value) in (int, float) and math.isfinite(value)


def validate_observer(native_tick, nominal_sim_time_s, raw_actual_elapsed_s):
    require(type(native_tick) is int and native_tick >= 0, 'invalid_native_tick')
    require(finite_time(nominal_sim_time_s) and finite_time(raw_actual_elapsed_s), 'invalid_clock_scalar')
    require(abs(nominal_sim_time_s - native_tick * NOMINAL_DT) < NOMINAL_TOLERANCE, 'nominal_clock_changed')
    expected = native_tick * CALLBACK32_DT
    residual = raw_actual_elapsed_s - expected
    require(abs(residual) <= ACTUAL_TOLERANCE, 'callback32_observer_clock_diverged')
    return {'version': VERSION, 'native_tick': native_tick, 'expected_actual_elapsed_s': expected,
            'raw_actual_elapsed_s': raw_actual_elapsed_s, 'residual_s': residual}


def bind_initial_row(first):
    require(type(first['tick']) is int and first['tick'] == 0, 'initial_recorded_tick_not_zero')
    native = first['native_tick']
    require(type(native) is int and native >= 0, 'invalid_original_initial_tick')
    validate_recorded(first, native)
    return native


def validate_recorded(row, initial_native_tick):
    native, relative = row['native_tick'], row['tick']
    require(type(initial_native_tick) is int and initial_native_tick >= 0, 'invalid_original_initial_tick')
    require(type(native) is int and type(relative) is int and relative >= 0, 'invalid_recorded_tick')
    require(native - relative == initial_native_tick, 'native_relative_receipt_binding_changed')
    nominal, actual = row['sim_time_s'], row['actual_physics_elapsed_s']
    require(finite_time(nominal) and finite_time(actual), 'invalid_clock_scalar')
    require(abs(nominal - relative * NOMINAL_DT) < NOMINAL_TOLERANCE, 'nominal_clock_changed')
    expected = native * CALLBACK32_DT - initial_native_tick * NOMINAL_DT
    residual = actual - expected
    require(abs(residual) < ACTUAL_TOLERANCE, 'callback32_recorded_clock_diverged')
    return {'version': VERSION, 'native_tick': native, 'relative_tick': relative,
            'initial_native_tick': initial_native_tick, 'expected_recorded_actual_s': expected,
            'raw_actual_physics_elapsed_s': actual, 'residual_s': residual}


def contract_receipt(initial_native_tick):
    require(type(initial_native_tick) is int and initial_native_tick >= 0, 'invalid_original_initial_tick')
    return {'version': VERSION, 'initial_native_tick': initial_native_tick,
            'nominal_dt_s': NOMINAL_DT, 'callback32_dt_s': CALLBACK32_DT,
            'nominal_tolerance_s': NOMINAL_TOLERANCE, 'actual_tolerance_s': ACTUAL_TOLERANCE,
            'observer_actual_comparison': '<=', 'recorded_actual_comparison': '<',
            'raw_time_fields_rewritten': False, 'simulator_dt_changed': False,
            'recorder_record_changed': False, 'original_c437_clock_unchanged': False}


def validate_episode_binding(receipt, first, direct_initial_receipt):
    initial = bind_initial_row(first)
    expected = contract_receipt(initial)
    require(type(receipt) is dict and receipt.keys() == expected.keys()
            and all(type(receipt[key]) is type(value) and receipt[key] == value
                    for key, value in expected.items()), 'native_clock_contract_receipt_changed')
    require(direct_initial_receipt['actual_native_initial_tick'] == initial
            and type(direct_initial_receipt['actual_native_initial_tick']) is int,
            'native_clock_initial_receipt_binding_changed')
    return initial
