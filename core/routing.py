from django.urls import re_path
from . import consumers

websocket_urlpatterns = [
    re_path(r"ws/track/(?P<booking_id>\d+)/$", consumers.TrackingConsumer.as_asgi()),
    re_path(r"ws/driver/(?P<driver_id>\d+)/$",  consumers.DriverConsumer.as_asgi()),
]           #idk 