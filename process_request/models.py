from django.contrib.auth.models import AbstractUser, AbstractBaseUser
from django.db import models


class User(AbstractUser):

    archivist_group = [u"rac_archivists"]
    donor_group = [u"rac_donors"]
    researcher_group = [u"rac_researchers"]

    AbstractUser._meta.get_field("email").blank = False
    AbstractUser._meta.get_field("first_name").blank = False
    AbstractUser._meta.get_field("last_name").blank = False
    AbstractUser._meta.get_field("username").blank = False

    @property
    def full_name(self):
        """
        Return the first_name plus the last_name, with a space in between.
        """
        full_name = '%s %s' % (self.first_name, self.last_name)
        return full_name.strip()

    def __str__(self):
        """
        Returns the full name and email of a user.
        """
        return '{} <{}>'.format(self.full_name, self.email)


class MachineUser(AbstractBaseUser):
    username = None
    system_name = models.CharField(blank=False, max_length=255, unique=True)
    host_location = models.URLField(blank=False)
    api_key = models.CharField(blank=False, max_length=255)

    is_active = models.BooleanField(
        default=True,
    )

    USERNAME_FIELD = 'system_name'

    def __str__(self):
        """
        Returns the system name.
        """
        return self.system_name
