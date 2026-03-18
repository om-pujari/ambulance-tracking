from django.db import models
from django.core.validators import RegexValidator
from django.contrib.auth.models import AbstractUser

# phno validation
phone_regex = RegexValidator(
    regex=r'^\+?1?\d{9,15}$',
    message="Phone number must be entered in the format: '+999999999'. Up to 15 digits allowed."
)


class User(AbstractUser):           # already inclueds password,username
    phno = models.CharField(max_length = 15,validators=[phone_regex])
    email = models.EmailField(unique=True,blank = True)

    role_choices = [
        ("Admin","admin"),
        ("Driver","driver"),
    ]
    
    roles = models.CharField(max_length=20,choices=role_choices ,blank=True, null=True)



class Booking(models.Model):
    phno = models.CharField(max_length = 15,validators=[phone_regex])

    pickup_lat = models.FloatField()
    pickup_long = models.FloatField()

    drop_lat = models.FloatField(null=True,blank=True)
    drop_long = models.FloatField(null=True,blank=True)

    ambulance_types = [
        ("ICU","Advance cardiac care"),
        ("ALS","Advance life support"),
        ("BLS","Basic life support "),
    ]
    hospital_pref = [
        ("Gov","Governement"),
        ("Pri","Private"),
        ("near","Nearest"),
    ]
    ambulance_type = models.CharField(max_length = 20, choices=ambulance_types)
    hospital_prefrences = models.CharField(max_length = 20, choices=hospital_pref)

    assigned_hosp = models.ForeignKey("Hospital",
                                      on_delete=models.SET_NULL,
                                      null=True,
                                      blank=True
                                      )

    assigned_driver = models.ForeignKey("driver.Driver",
                                        on_delete=models.SET_NULL,
                                        null=True,
                                        blank = True 
                                        )

    status_choices = [
        ("pending","pending"),
        ("assigned","assigned"),
        ("in_progress","in_progress"),
        ("completed","completed"),
        ("terminated","terminated"),
    ]
    status = models.CharField(max_length = 20, choices=status_choices,default="pending")
    created_at = models.DateTimeField(auto_now_add=True)

    
class Hospital(models.Model):
    name = models.CharField(max_length=30)
    hosp_type = [
        ("gov","Governement"),
        ("pri","Private"),
    ]
    hosp = models.CharField(max_length = 30,choices=hosp_type)
    lat = models.FloatField()
    long = models.FloatField()
    is_active = models.BooleanField(default=True)


class OTP(models.Model):
    phone = models.CharField(max_length=15)

    code = models.CharField(max_length=6)

    is_verified = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)

    def is_expired(self):
        from django.utils import timezone
        return timezone.now() > self.created_at + timezone.timedelta(minutes=5)
    