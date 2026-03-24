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


import asyncio
from channels.layers import get_channel_layer
from asgiref.sync import sync_to_async

channel_layer = get_channel_layer()
DRIVER_TIMEOUT = 10  # seconds to wait for driver to accept


async def dispatch_booking_async(booking_id, excluded_driver_ids=None):
    """
    Async retry loop:
    1. Get nearby ONLINE drivers (sorted by distance)
    2. Loop: send request → wait 10s → if accepted → done, else → next driver
    3. If none accept → mark FAILED (terminated)
    """
    excluded_driver_ids = excluded_driver_ids or []

    booking = await get_booking(booking_id)
    if not booking:
        return

    drivers = await get_sorted_drivers(booking, excluded_driver_ids)

    if not drivers:
        await mark_terminated(booking_id)
        await notify_user(booking_id, "terminated", "No drivers available")
        return

    for driver in drivers:
        # Push dispatch request to driver's WebSocket group
        await channel_layer.group_send(
            f"driver_{driver['id']}",
            {
                "type": "dispatch_request",
                "booking_id": booking_id,
                "pickup_lat": booking["pickup_lat"],
                "pickup_lng": booking["pickup_long"],
                "hospital_name": booking["hospital_name"],
                "ambulance_type": booking["ambulance_type"],
            }
        )

        # Notify user: we're looking
        await notify_user(booking_id, "pending", f"Waiting for driver to accept...")

        # Wait up to DRIVER_TIMEOUT seconds for driver to accept
        accepted = await wait_for_acceptance(booking_id, timeout=DRIVER_TIMEOUT)

        if accepted:
            return  # Driver accepted — consumers handle the rest

        # Driver didn't respond — exclude and try next
        excluded_driver_ids.append(driver["id"])

    # All drivers exhausted
    await mark_terminated(booking_id)
    await notify_user(booking_id, "terminated", "No drivers accepted. Please try again.")


async def wait_for_acceptance(booking_id, timeout):
    """Poll DB every second for up to `timeout` seconds."""
    for _ in range(timeout):
        await asyncio.sleep(1)
        status = await get_booking_status(booking_id)
        if status == "assigned":
            return True
    return False


async def notify_user(booking_id, status, message):
    # Fetch extra details to show on tracking page
    booking = await get_booking_with_details(booking_id)
    await channel_layer.group_send(
        f"booking_{booking_id}",
        {
            "type": "booking_update",
            "status": status,
            "message": message,
            "driver_name": booking["driver_name"] if booking else "",
            "hospital_name": booking["hospital_name"] if booking else "",
        }
    )

@sync_to_async
def get_booking_with_details(booking_id):
    from core.models import Booking
    try:
        b = Booking.objects.select_related("assigned_driver__user", "assigned_hosp").get(pk=booking_id)
        return {
            "driver_name": b.assigned_driver.user.username if b.assigned_driver else "",
            "hospital_name": b.assigned_hosp.name if b.assigned_hosp else "",
        }
    except Booking.DoesNotExist:
        return None
# ---- DB helpers ----

@sync_to_async
def get_booking(booking_id):
    from core.models import Booking
    try:
        b = Booking.objects.select_related("assigned_hosp").get(pk=booking_id)
        return {
            "pickup_lat": b.pickup_lat,
            "pickup_long": b.pickup_long,
            "ambulance_type": b.ambulance_type,
            "hospital_name": b.assigned_hosp.name if b.assigned_hosp else "TBD",
            "status": b.status,
        }
    except Booking.DoesNotExist:
        return None

@sync_to_async
def get_booking_status(booking_id):
    from core.models import Booking
    return Booking.objects.filter(pk=booking_id).values_list("status", flat=True).first()

@sync_to_async
def get_sorted_drivers(booking, excluded_ids):
    import math
    from driver.models import Driver

    def distance(lat1, lon1, lat2, lon2):
        return math.sqrt((lat1 - lat2) ** 2 + (lon1 - lon2) ** 2)

    drivers = Driver.objects.filter(
        state="On",
        ambulance_type=booking["ambulance_type"]
    ).exclude(pk__in=excluded_ids).select_related("user")

    result = []
    for d in drivers:
        if d.current_lat is not None and d.current_long is not None:
            dist = distance(booking["pickup_lat"], booking["pickup_long"], d.current_lat, d.current_long)
            result.append({"id": d.pk, "dist": dist})

    return sorted(result, key=lambda x: x["dist"])

@sync_to_async
def mark_terminated(booking_id):
    from core.models import Booking
    Booking.objects.filter(pk=booking_id).update(status="terminated")