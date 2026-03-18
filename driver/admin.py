from django.contrib import admin
from core.models import User,OTP,Booking,Hospital
from driver.models import Driver

admin.site.register(User)
admin.site.register(OTP)
admin.site.register(Booking)
admin.site.register(Hospital)
admin.site.register(Driver)