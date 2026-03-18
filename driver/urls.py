from django.urls import path
from . import views

urlpatterns = [
    path("login/", views.driver_login, name="driver_login"),
    path("logout/",views.driver_logout,name= "driver_logout"),
    path("dashboard/", views.driver_dashboard, name="driver_dashboard"),
    path("update-location/", views.update_driver_location, name="update_driver_location"),
    path("accept-booking/", views.accept_booking, name="accept_booking"),
    path("reject-booking/", views.reject_booking, name="reject_booking"),
    path("start-trip/", views.start_trip, name="start_trip"),
    path("complete-trip/", views.complete_trip, name="complete_trip"),
    path("toggle/", views.toggle_driver_state, name="toggle_driver_state"),
]
