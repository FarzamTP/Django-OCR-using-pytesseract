from django.db import models
from django.db.models.signals import post_save
from django.contrib.auth.models import User


# Create your models here.
class UserProfile(models.Model):
    user = models.OneToOneField(User, default=None, on_delete=models.CASCADE)

    def __str__(self):
        return self.user.username


class Receipt(models.Model):
    title = models.CharField(max_length=128)
    raw_image_url = models.CharField(max_length=256)
    processed_image_url = models.CharField(max_length=256)
    contributors = models.ManyToManyField(UserProfile)

    def __str__(self):
        return f'Receipt for {self.title}'


def create_profile(sender, **kwargs):
    if kwargs['created']:
        UserProfile.objects.create(user=kwargs['instance'])


post_save.connect(receiver=create_profile, sender=User)

