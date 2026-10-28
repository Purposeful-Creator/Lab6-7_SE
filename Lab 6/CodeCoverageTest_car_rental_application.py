import pytest
from car_rental_rate import process_rental_fleet, check_fleet_telematics


def rental(**kwargs):
    """Build a confirmed rental; any field can be overridden."""
    base = {"is_confirmed": True, "vehicle_type": "economy",
            "driver_age": 30, "days": 1, "trip_segments": []}
    base.update(kwargs)
    return base


# ---------- process_rental_fleet ----------
def test_single_economy_rental():
    result = process_rental_fleet([rental(days=2, trip_segments=[100])], 10.0)
    assert result["total_revenue"] == 110.0
    assert result["status"] == "STANDARD"


def test_invalid_rentals_type_raises():
    with pytest.raises(ValueError):
        process_rental_fleet("not a list", 10.0)


def test_negative_admin_fee_raises():
    with pytest.raises(ValueError):
        process_rental_fleet([rental()], -1.0)


def test_unconfirmed_rental_is_skipped():
    result = process_rental_fleet([rental(is_confirmed=False)], 10.0)
    assert result == {"total_revenue": 0.0, "status": "EMPTY_BATCH"}


def test_non_positive_days_is_risk_flag():
    result = process_rental_fleet([rental(days=0)], 10.0)
    assert result == {"total_revenue": 0.0, "status": "EMPTY_BATCH"}


def test_luxury_rental():
    result = process_rental_fleet([rental(vehicle_type="luxury", days=3)], 0.0)
    assert result == {"total_revenue": 360.0, "status": "STANDARD"}


def test_suv_rental_short_trip():
    result = process_rental_fleet(
        [rental(vehicle_type="suv", driver_age=40, trip_segments=[50])], 5.0)
    assert result["total_revenue"] == 85.0          # 70 + 5 + 50*0.20


def test_long_trip_adult_driver_pays_per_mile_surcharge():
    result = process_rental_fleet([rental(trip_segments=[400])], 0.0)
    assert result["total_revenue"] == 200.0         # 40 + 400*0.40


def test_long_trip_underage_driver_flat_fee_and_stops_counting_segments():
    result = process_rental_fleet(
        [rental(driver_age=20, trip_segments=[500, 100])], 0.0)
    assert result["total_revenue"] == 310.0         # 40 + 250 + young-driver 20


def test_negative_miles_is_risk_flag_and_skipped():
    result = process_rental_fleet([rental(trip_segments=[-5, 100])], 0.0)
    assert result["total_revenue"] == 60.0          # 40 + 100*0.20


def test_young_driver_surcharge_non_luxury():
    result = process_rental_fleet([rental(driver_age=22, days=2)], 0.0)
    assert result["total_revenue"] == 120.0         # 80 + 20*2


def test_young_driver_surcharge_luxury():
    result = process_rental_fleet(
        [rental(vehicle_type="luxury", driver_age=23, days=2)], 0.0)
    assert result["total_revenue"] == 340.0         # 240 + 50*2


def test_high_risk_audit_when_more_than_four_flags():
    rentals = [rental(days=0) for _ in range(5)] + [rental()]
    result = process_rental_fleet(rentals, 0.0)
    assert result == {"total_revenue": 40.0, "status": "HIGH_RISK_AUDIT"}


# ---------- check_fleet_telematics ----------
def test_telematics_no_data():
    assert check_fleet_telematics([]) == "NO_DATA"


def test_telematics_two_consecutive_speeds_grounds_vehicle():
    assert check_fleet_telematics([[90, 101, 102]]) == "GROUND_VEHICLE"


def test_telematics_isolated_speeding_is_safe():
    assert check_fleet_telematics([[50, 120, 60, 130, 70]]) == "SAFE"
