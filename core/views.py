from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, render, redirect
import random
from django.http import JsonResponse
from .models import OTP, Booking
from core.services import dispatch_booking
from driver.models import Driver
from asgiref.sync import async_to_sync
from .services import dispatch_booking_async, notify_user

# Inside your booking creation view, after calling dispatch_booking():


def is_ajax(request):
    return request.headers.get("x-requested-with") == "XMLHttpRequest"

def landing(request):
    return render(request, "core/landing.html")

def phone_page(request):
    return render(request, "core/booking.html")


def send_otp(request):
    phone = request.POST.get("phone")

    code = str(random.randint(100000, 999999))

    OTP.objects.create(
        phone=phone,
        code=code
    )

    print("OTP:", code)   # for testing

    return JsonResponse({"status": "sent"})


def verify_otp(request):
    phone = request.POST.get("phone")
    code = request.POST.get("code")

    try:
        otp = OTP.objects.filter(phone=phone).latest("created_at")

        if otp.code == code:
            otp.is_verified = True
            otp.save()
            request.session["phone"] = phone
            if is_ajax(request):
                return JsonResponse({"status": "verified"})
            return redirect("ambulance_select")

    except OTP.DoesNotExist:
        pass

    return JsonResponse({"status": "invalid"})

def ambulance_select(request):
    return render(request, "core/booking.html")

def hospital_pref(request):
    if request.method == "POST":
        request.session["ambulance_type"] = request.POST.get("ambulance_type")
        if is_ajax(request):
            return JsonResponse({"status": "saved"})
        return render(request, "core/hospital_pref.html")
    return redirect("phone_page")


def create_booking(request):                #fine tune later to avoid redundant booking from user pages 
    if request.method == "POST":

        phone = request.session.get("phone")
        ambulance_type = request.session.get("ambulance_type") or request.POST.get("ambulance_type")
        hospital_pref = request.POST.get("hospital_pref")

        if not phone or not ambulance_type or not hospital_pref:
            return JsonResponse({"status": "error", "message": "Missing booking details."}, status=400)

        try:
            lat = round(float(request.POST.get("lat")), 5)
            lon = round(float(request.POST.get("lon")), 5)
        except (TypeError, ValueError):
            lat = 0
            lon = 0

        booking = Booking.objects.create(
            phno=phone,
            ambulance_type=ambulance_type,
            hospital_prefrences=hospital_pref,
            pickup_lat=lat,
            pickup_long=lon,
            status="pending"
        )

        dispatched = dispatch_booking(booking)
        print("After sync dispatch — status:", booking.status, "driver:", booking.assigned_driver_id)

        async_to_sync(notify_user)(
            booking.id,
            "assigned" if dispatched else "terminated",
            "Driver assigned!" if dispatched else "No drivers available right now."
        )
        if is_ajax(request):
            return JsonResponse({
                "status": "created",
                "booking_id": booking.id,
                "phone": booking.phno,
                "ambulance_type": booking.ambulance_type,
                "hospital_preference": booking.hospital_prefrences,
                "booking_status": booking.status,
                "tracking_url": f"/booking/{booking.id}/track/",
            })

        return render(request, "core/booking_done.html", {"booking": booking})
    return redirect("phone_page")


def track_booking(request, booking_id):
    session_phone = request.session.get("phone")
    booking = get_object_or_404(Booking.objects.select_related("assigned_driver__user", "assigned_hosp"), pk=booking_id)

    if session_phone and booking.phno != session_phone:
        return redirect("phone_page")

    return render(request, "core/booking_done.html", {"booking": booking})


def booking_status(request, booking_id):
    session_phone = request.session.get("phone")
    booking = get_object_or_404(Booking.objects.select_related("assigned_driver__user", "assigned_hosp"), pk=booking_id)

    if session_phone and booking.phno != session_phone:
        return JsonResponse({"status": "forbidden"}, status=403)

    driver = booking.assigned_driver
    hospital = booking.assigned_hosp
    return JsonResponse({
        "booking_id": booking.id,
        "status": booking.status,
        "pickup_lat": booking.pickup_lat,
        "pickup_lng": booking.pickup_long,
        "hospital_name": hospital.name if hospital else "Pending hospital",
        "hospital_lat": booking.drop_lat,
        "hospital_lng": booking.drop_long,
        "driver_name": driver.user.get_full_name() if driver and driver.user.get_full_name() else (driver.user.username if driver else "Pending assignment"),
        "driver_phone": driver.user.phno if driver else "",
        "driver_lat": driver.current_lat if driver else None,
        "driver_lng": driver.current_long if driver else None,
    })


def update_booking_location(request, booking_id):
    if request.method != "POST":
        return JsonResponse({"status": "invalid"}, status=405)

    session_phone = request.session.get("phone")
    booking = get_object_or_404(Booking, pk=booking_id)

    if session_phone and booking.phno != session_phone:
        return JsonResponse({"status": "forbidden"}, status=403)

    try:
        booking.pickup_lat = round(float(request.POST.get("lat")), 5)
        booking.pickup_long = round(float(request.POST.get("lon")), 5)
    except (TypeError, ValueError):
        return JsonResponse({"status": "invalid"}, status=400)

    booking.save(update_fields=["pickup_lat", "pickup_long"])
    return JsonResponse({"status": "ok"})


@login_required
def admin_dashboard(request):
    drivers = [
        {
            "name": driver.user.get_full_name() or driver.user.username,
            "state": driver.state,
            "ambulance_type": driver.ambulance_type,
            "lat": driver.current_lat,
            "lng": driver.current_long,
        }
        for driver in Driver.objects.select_related("user")
        if driver.current_lat is not None and driver.current_long is not None
    ]

    bookings = [
        {
            "phone": booking.phno,
            "status": booking.status,
            "ambulance_type": booking.ambulance_type,
            "lat": booking.pickup_lat,
            "lng": booking.pickup_long,
        }
        for booking in Booking.objects.all().order_by("-created_at")[:100]
    ]

    return render(request, "admin/admin_dashboard.html", {
        "drivers_data": drivers,
        "bookings_data": bookings,
    })
