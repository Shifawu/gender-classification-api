from django.db import models
import uuid

# Create your models here.

class Profile(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=225, unique=True)

    gender = models.CharField(max_length=10)
    gender_probability = models.FloatField()

    sample_size = models.IntegerField(null=True, blank=True)

    age = models.IntegerField()
    age_group = models.CharField(max_length=20)

    country_id = models.CharField(max_length=5)
    country_probability = models.FloatField()
    country_name = models.CharField(max_length=100, default="Unknwon")

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name