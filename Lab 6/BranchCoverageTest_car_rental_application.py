import pytest
from car_rental_rate import process_rental_fleet, check_fleet_telematics


def rental(**kwargs):
    base = {"is_confirmed": True, "vehicle_type": "economy",
            "driver_age": 30, "days": 1, "trip_segments": []}
    base.update(kwargs)
    return base


# --- validation: both sides of `not list or fee < 0` ---
def test_rentals_not_a_list():
    with pytest.raises(ValueError):
        process_rental_fleet({"a": 1}, 10.0)


def test_fee_negative():
    with pytest.raises(ValueError):
        process_rental_fleet([], -0.01)


def test_valid_inputs_do_not_raise():
    assert process_rental_fleet([rental()], 0.0)["status"] == "STANDARD"


# --- is_confirmed True / False ---
def test_confirmed_and_unconfirmed_mix():
    r = process_rental_fleet([rental(is_confirmed=False), rental()], 0.0)
    assert r["total_revenue"] == 40.0


# --- days <= 0 / > 0 ---
def test_days_zero_and_negative_flagged():
    r = process_rental_fleet([rental(days=0), rental(days=-2)], 0.0)
    assert r["status"] == "EMPTY_BATCH"


# --- vehicle type: luxury / suv / other ---
@pytest.mark.parametrize("vtype,expected", [("luxury", 120.0), ("suv", 70.0), ("economy", 40.0)])
def test_vehicle_rates(vtype, expected):
    r = process_rental_fleet([rental(vehicle_type=vtype)], 0.0)
    assert r["total_revenue"] == expected


# --- trip segment branches: <0, >300 (age<21 / age>=21), normal, loop with no segments ---
def test_segment_negative():
    r = process_rental_fleet([rental(trip_segments=[-1])], 0.0)
    assert r["total_revenue"] == 40.0


def test_segment_over_300_adult():
    r = process_rental_fleet([rental(trip_segments=[301])], 0.0)
    assert r["total_revenue"] == pytest.approx(40 + 301 * 0.40, abs=0.01)


def test_segment_over_300_underage_breaks():
    r = process_rental_fleet([rental(driver_age=20, trip_segments=[400, 100])], 0.0)
    assert r["total_revenue"] == 310.0


def test_segment_normal_and_boundary_300():
    r = process_rental_fleet([rental(trip_segments=[300, 0])], 0.0)
    assert r["total_revenue"] == 100.0


def test_no_segments():
    assert process_rental_fleet([rental()], 5.0)["total_revenue"] == 45.0


# --- driver_age < 25: luxury / non-luxury; and age >= 25 (boundary) ---
def test_young_driver_luxury():
    r = process_rental_fleet([rental(vehicle_type="luxury", driver_age=24)], 0.0)
    assert r["total_revenue"] == 170.0


def test_young_driver_non_luxury():
    r = process_rental_fleet([rental(driver_age=24)], 0.0)
    assert r["total_revenue"] == 60.0


def test_age_25_no_surcharge():
    r = process_rental_fleet([rental(driver_age=25)], 0.0)
    assert r["total_revenue"] == 40.0


# --- final status: risk_flags >4 / ==4 boundary / empty / standard ---
def test_five_flags_high_risk():
    r = process_rental_fleet([rental(days=0)] * 5, 0.0)
    assert r["status"] == "HIGH_RISK_AUDIT"


def test_four_flags_not_high_risk():
    r = process_rental_fleet([rental(days=0)] * 4 + [rental()], 0.0)
    assert r["status"] == "STANDARD"


def test_empty_list_is_empty_batch():
    assert process_rental_fleet([], 0.0) == {"total_revenue": 0.0, "status": "EMPTY_BATCH"}


# --- telematics ---
def test_telematics_empty():
    assert check_fleet_telematics([]) == "NO_DATA"


def test_telematics_grounded():
    assert check_fleet_telematics([[101, 102]]) == "GROUND_VEHICLE"


def test_telematics_streak_resets():
    assert check_fleet_telematics([[101, 50, 101, 50]]) == "SAFE"


def test_telematics_streak_does_not_carry_across_vehicles():
    assert check_fleet_telematics([[50, 101], [101, 50]]) == "SAFE"


def test_telematics_vehicle_with_no_logs():
    assert check_fleet_telematics([[]]) == "SAFE"
