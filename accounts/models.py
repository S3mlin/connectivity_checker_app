import uuid
from django.contrib import auth
from django.db import models
from accounts.managers import CustomUserManager
from django.contrib.auth.models import AbstractBaseUser
from django.contrib.auth.models import PermissionsMixin

auth.signals.user_logged_in.disconnect(auth.models.update_last_login)


class User(AbstractBaseUser, PermissionsMixin):
    email = models.EmailField(primary_key=True)
    is_staff = models.BooleanField(default=False)
    is_superuser = models.BooleanField(default=False)
    password = models.CharField(null=True)

    REQUIRED_FIELDS = []
    USERNAME_FIELD = "email"
    is_anonymous = False
    is_authenticated = True

    objects = CustomUserManager()


class Token(models.Model):
    email = models.EmailField()
    uid = models.CharField(default=uuid.uuid4, max_length=40)
