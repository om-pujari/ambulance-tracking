import math

from core.models import Hospital
from driver.models import Driver


def distance(lat1, lon1, lat2, lon2):
    return math.sqrt((lat1-lat2)**2 + (lon1-lon2)**2)


def dispatch_booking(booking, excluded_driver_ids=None):
    excluded_driver_ids = excluded_driver_ids or []

    pickup_lat = booking.pickup_lat
    pickup_lon = booking.pickup_long

    # ---- select hospital ----
    if booking.hospital_prefrences == "Gov":
        hospitals = Hospital.objects.filter(hosp="gov", is_active=True)

    elif booking.hospital_prefrences == "Pri":
        hospitals = Hospital.objects.filter(hosp="pri", is_active=True)

    else:
        hospitals = Hospital.objects.filter(is_active=True)

    hospitals = list(hospitals)
    if not hospitals:
        return False

    nearest_hosp = min(hospitals, key=lambda h: distance(pickup_lat, pickup_lon, h.lat, h.long))

    booking.assigned_hosp = nearest_hosp
    booking.drop_lat = nearest_hosp.lat
    booking.drop_long = nearest_hosp.long

    # ---- select driver ----
    drivers = Driver.objects.filter(
        state="On",
        ambulance_type=booking.ambulance_type
    ).exclude(pk__in=excluded_driver_ids)

    drivers = [driver for driver in drivers if driver.current_lat is not None and driver.current_long is not None]
    if not drivers:
        booking.assigned_driver = None
        booking.status = "pending"
        booking.save()
        return False

    nearest_driver = min(drivers, key=lambda d: distance(pickup_lat, pickup_lon, d.current_lat, d.current_long))

    booking.assigned_driver = nearest_driver
    booking.status = "assigned"

    nearest_driver.state = "Busy"

    nearest_driver.save()
    booking.save()
    return True
