from django.db import models
from core.models import User
from django.core.validators import RegexValidator


phone_regex = RegexValidator(
    regex=r'^\+?1?\d{9,15}$',
    message="Phone number must be entered in the format: '+999999999'. Up to 15 digits allowed."
)

license_key_validator = RegexValidator(
    regex=r'^[A-Z0-9]{5}$',
    message='Enter a valid license key (5 alphanumeric characters).'
)

class Driver(models.Model):
    user = models.OneToOneField(User,on_delete=models.CASCADE)
    licens = models.CharField(max_length = 20, validators=[license_key_validator])
    current_lat = models.FloatField(null=True, blank=True)
    current_long = models.FloatField(null=True, blank=True)

    states_choices = [
        ("On","Online"),
        ("Off","Offline"),
        ("Busy","En route"),
        ("Accidents","Accident"),
    ]
    ambulance_type = models.CharField(
        max_length=10,
        choices=[
            ("ICU","ICU"),
            ("ALS","ALS"),
            ("BLS","BLS")
        ]
    )  
    state = models.CharField(max_length = 20, choices=states_choices)