from django.urls import path
from . import views

urlpatterns = [
    path('', views.landing, name='landing'),
    path("book/", views.phone_page, name="phone_page"),
    path("booking/<int:booking_id>/track/", views.track_booking, name="track_booking"),
    path("booking/<int:booking_id>/status/", views.booking_status, name="booking_status"),
    path("booking/<int:booking_id>/update-location/", views.update_booking_location, name="update_booking_location"),
    path("ops/admin-dashboard/", views.admin_dashboard, name="admin_dashboard"),
    path("send-otp/", views.send_otp, name="send_otp"),
    path("verify-otp/", views.verify_otp, name="verify_otp"),
    path("ambulance/", views.ambulance_select, name="ambulance_select"),
    path("hospital-pref/", views.hospital_pref, name="hospital_pref"),
    path("create-booking/", views.create_booking, name="create_booking"),
]
