from django.contrib import admin
from core.models import User,OTP,Booking,Hospital
from driver.models import Driver

@admin.register(Booking)
class BookingAdmin(admin.ModelAdmin):
    list_display  = ["id", "phno", "status", "ambulance_type", "hospital_prefrences", "assigned_driver", "assigned_hosp", "created_at"]
    list_filter   = ["status", "ambulance_type", "hospital_prefrences"]
    search_fields = ["phno"]
    ordering      = ["-created_at"]

@admin.register(Hospital)
class HospitalAdmin(admin.ModelAdmin):
    list_display  = ["name", "hosp", "lat", "long", "is_active"]
    list_filter   = ["hosp", "is_active"]

@admin.register(Driver)
class DriverAdmin(admin.ModelAdmin):
    list_display  = ["user", "ambulance_type", "state", "current_lat", "current_long", "licens"]
    list_filter   = ["state", "ambulance_type"]
    search_fields = ["user__username", "licens"]

@admin.register(OTP)
class OTPAdmin(admin.ModelAdmin):
    list_display  = ["phone", "code", "is_verified", "created_at"]

@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display  = ["username", "email", "phno", "roles", "is_staff"]
    search_fields = ["username", "email", "phno"]