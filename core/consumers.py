import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from core.models import Booking
from driver.models import Driver


class TrackingConsumer(AsyncWebsocketConsumer):
    """
    User opens this after booking.
    They join a group named "booking_{id}".
    Driver location updates get pushed here in real time.
    """

    async def connect(self):
        self.booking_id = self.scope["url_route"]["kwargs"]["booking_id"]
        self.group_name = f"booking_{self.booking_id}"

        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()
        # Send full current state immediately on connect
        booking = await self.get_booking()
        if booking:
            await self.send(text_data=json.dumps({
                "type": "booking_update",
                "status": booking["status"],
                "message": self.status_message(booking["status"]),
                "driver_name": booking["driver_name"],
                "hospital_name": booking["hospital_name"],
            }))


    def status_message(self, status):
        return {
            "pending":     "Looking for a driver...",
            "assigned":    "Driver has been assigned!",
            "in_progress": "Ambulance is on the way!",
            "completed":   "Booking completed.",
            "terminated":  "No drivers available.",
        }.get(status, "")

    async def disconnect(self, code):
        await self.channel_layer.group_discard(self.group_name, self.channel_name)

    # Receive message from frontend (not used for tracking, but kept for extensibility)
    async def receive(self, text_data):
        pass

    # Called when driver pushes a location update to this group
    async def driver_location(self, event):
        await self.send(text_data=json.dumps({
            "type": "driver_location",
            "lat": event["lat"],
            "lng": event["lng"],
        }))

    # Called when booking status changes (assigned, in_progress, completed, terminated)
    async def booking_update(self, event):
        await self.send(text_data=json.dumps({
            "type": "booking_update",
            "status": event["status"],
            "message": event.get("message", ""),
            "driver_name": event.get("driver_name", ""),
            "hospital_name": event.get("hospital_name", ""),
        }))

    @database_sync_to_async
    
    def get_booking(self):
        try:
            b = Booking.objects.select_related(
                "assigned_driver__user", "assigned_hosp"
            ).get(pk=self.booking_id)
            return {
                "status": b.status,
                "driver_id": b.assigned_driver_id,
                "driver_name": b.assigned_driver.user.username if b.assigned_driver else "",
                "hospital_name": b.assigned_hosp.name if b.assigned_hosp else "",
            }
        except Booking.DoesNotExist:
            return None


class DriverConsumer(AsyncWebsocketConsumer):
    """
    Driver app connects here.
    Receives dispatch requests, accepts/rejects them.
    Pushes location updates back to the user's tracking group.
    """

    async def connect(self):
        self.driver_id = self.scope["url_route"]["kwargs"]["driver_id"]
        self.group_name = f"driver_{self.driver_id}"

        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()

    async def disconnect(self, code):
        await self.channel_layer.group_discard(self.group_name, self.channel_name)

    async def receive(self, text_data):
        data = json.loads(text_data)
        msg_type = data.get("type")

        if msg_type == "location_update":
            # Driver is sending their current GPS position
            await self.handle_location_update(data)

        elif msg_type == "accept_booking":
            await self.handle_accept(data)

        elif msg_type == "reject_booking":
            await self.handle_reject(data)

        elif msg_type == "status_update":
            # Driver marks booking as in_progress or completed
            await self.handle_status_update(data)

    async def handle_location_update(self, data):
        lat = data["lat"]
        lng = data["lng"]

        # Persist location to DB
        await self.save_driver_location(lat, lng)

        # Push to the user who is tracking this driver's active booking
        booking_id = await self.get_active_booking_id()
        if booking_id:
            await self.channel_layer.group_send(
                f"booking_{booking_id}",
                {
                    "type": "driver_location",  # maps to TrackingConsumer.driver_location()
                    "lat": lat,
                    "lng": lng,
                }
            )

    async def handle_accept(self, data):
        booking_id = data["booking_id"]
        success = await self.assign_driver_to_booking(booking_id)
        if success:
            # Notify the user's tracking group
            await self.channel_layer.group_send(
                f"booking_{booking_id}",
                {
                    "type": "booking_update",
                    "status": "assigned",
                    "message": "Driver accepted your request",
                }
            )
            # Confirm back to driver
            await self.send(text_data=json.dumps({
                "type": "accept_confirmed",
                "booking_id": booking_id,
            }))

    async def handle_reject(self, data):
        booking_id = data["booking_id"]
        # Mark driver as excluded and re-trigger dispatch
        await self.free_driver()
        # Import here to avoid circular imports
        from .services import dispatch_booking_async
        await dispatch_booking_async(booking_id, excluded_driver_ids=[int(self.driver_id)])

    async def handle_status_update(self, data):
        booking_id = data["booking_id"]
        new_status = data["status"]  # "in_progress" or "completed"

        await self.update_booking_status(booking_id, new_status)

        await self.channel_layer.group_send(
            f"booking_{booking_id}",
            {
                "type": "booking_update",
                "status": new_status,
                "message": f"Booking is now {new_status}",
            }
        )

        if new_status == "completed":
            await self.free_driver()

    # Called by dispatch — sends a job request to this driver
    async def dispatch_request(self, event):
        await self.send(text_data=json.dumps({
            "type": "dispatch_request",
            "booking_id": event["booking_id"],
            "pickup_lat": event["pickup_lat"],
            "pickup_lng": event["pickup_lng"],
            "hospital_name": event["hospital_name"],
            "ambulance_type": event["ambulance_type"],
        }))

    # ---- DB helpers ----

    @database_sync_to_async
    def save_driver_location(self, lat, lng):
        Driver.objects.filter(pk=self.driver_id).update(
            current_lat=lat, current_long=lng
        )

    @database_sync_to_async
    def get_active_booking_id(self):
        try:
            b = Booking.objects.filter(
                assigned_driver_id=self.driver_id,
                status__in=["assigned", "in_progress"]
            ).values_list("id", flat=True).first()
            return b
        except Exception:
            return None

    @database_sync_to_async
    def assign_driver_to_booking(self, booking_id):
        try:
            booking = Booking.objects.get(pk=booking_id, status="pending")
            booking.status = "assigned"
            booking.save()
            Driver.objects.filter(pk=self.driver_id).update(state="Busy")
            return True
        except Booking.DoesNotExist:
            return False

    @database_sync_to_async
    def update_booking_status(self, booking_id, status):
        Booking.objects.filter(pk=booking_id).update(status=status)

    @database_sync_to_async
    def free_driver(self):
        Driver.objects.filter(pk=self.driver_id).update(state="On")