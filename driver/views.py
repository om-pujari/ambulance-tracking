from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.http import require_POST

from core.services import dispatch_booking

def driver_login(request):
    error = None
    if request.method == "POST":
        username = request.POST.get("username")
        password = request.POST.get("password")

        user = authenticate(request, username=username, password=password)

        print(user)
        if user is not None:
            print(user)
            login(request, user)
            return redirect("driver_dashboard")
        error = "Invalid username or password."

    return render(request, "driver/login.html", {"error": error})


from core.models import Booking

@login_required
def driver_dashboard(request):

    driver = request.user.driver

    booking = Booking.objects.filter(
        assigned_driver=driver,
        status__in=["assigned", "in_progress"]
    ).first()

    driver_data = {
        "name": request.user.get_full_name() or request.user.username,
        "age": getattr(request.user, "age", None),
        "license": driver.licens,
        "ambulance_type": driver.ambulance_type,
        "state": driver.state,
        "lat": driver.current_lat,
        "lng": driver.current_long,
        "phone": request.user.phno,
    }

    booking_data = None
    if booking:
        booking_data = {
            "phone": booking.phno,
            "status": booking.status,
            "pickup_lat": booking.pickup_lat,
            "pickup_lng": booking.pickup_long,
            "hospital_lat": booking.drop_lat,
            "hospital_lng": booking.drop_long,
            "hospital_name": booking.assigned_hosp.name if booking.assigned_hosp else "Assigned hospital",
        }

    return render(request, "driver/dashboard.html", {
        "booking": booking,
        "driver_data": driver_data,
        "booking_data": booking_data,
    })

@login_required
def driver_logout(request):
    logout(request)
    return render(request,"driver/login.html")

@login_required
@require_POST
def update_driver_location(request):
    lat = round(float(request.POST.get("lat")), 5)
    lon = round(float(request.POST.get("lon")), 5)

    driver = request.user.driver
    driver.current_lat = lat
    driver.current_long = lon
    driver.save()
    print(driver.current_lat)

    return JsonResponse({"status": "ok"})

@login_required
@require_POST
def accept_booking(request):
    driver = request.user.driver
    booking = Booking.objects.filter(assigned_driver=driver, status="assigned").first()

    if not booking:
        return JsonResponse({"status": "missing"}, status=404)

    driver.state = "Busy"
    driver.save()
    return JsonResponse({"status": "accepted"})

@login_required
@require_POST
def reject_booking(request):
    driver = request.user.driver
    booking = Booking.objects.filter(assigned_driver=driver, status="assigned").first()

    if not booking:
        return JsonResponse({"status": "missing"}, status=404)

    driver.state = "On"
    driver.save()

    booking.assigned_driver = None
    booking.status = "pending"
    booking.save()

    reassigned = dispatch_booking(booking, excluded_driver_ids=[driver.pk])
    return JsonResponse({"status": "reassigned" if reassigned else "pending"})

@login_required
@require_POST
def start_trip(request):

    driver = request.user.driver

    booking = Booking.objects.filter(
        assigned_driver=driver,
        status="assigned"
    ).first()

    if booking:
        booking.status = "in_progress"
        booking.save()
        if request.headers.get("x-requested-with") == "XMLHttpRequest":
            return JsonResponse({"status": "started"})

    return redirect("driver_dashboard")

@login_required
@require_POST
def complete_trip(request):

    driver = request.user.driver

    booking = Booking.objects.filter(
        assigned_driver=driver,
        status="in_progress"
    ).first()

    if booking:
        booking.status = "completed"
        booking.save()

        driver.state = "On"
        driver.save()

        if request.headers.get("x-requested-with") == "XMLHttpRequest":
            return JsonResponse({"status": "completed"})

    return redirect("driver_dashboard")

@login_required
@require_POST
def toggle_driver_state(request):

    driver = request.user.driver
    state = request.POST.get("state")
        
    if state == "On":
        driver.state = "On"

    else:
        driver.state = "Off"

    driver.save()

    if request.headers.get("x-requested-with") == "XMLHttpRequest":
        return JsonResponse({"status": "ok", "state": driver.state})

    return redirect("driver_dashboard")
