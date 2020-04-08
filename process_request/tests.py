from django.test import TestCase

from .models import MachineUser, User

# Create your tests here.

class TestPackage(TestCase):

    def setUp(self):
        pass

    def test_full_name(self):
        name = 'Patrick Galligan'
        user = User.objects.create(first_name="Patrick", last_name="Galligan")
        self.assertEqual(user.full_name, name)

    def test_user_str(self):
        full_email = 'Patrick Galligan <pgalligan@rockarch.org>'
        user = User.objects.create(
            first_name="Patrick",
            last_name="Galligan",
            email="pgalligan@rockarch.org")
        self.assertEqual(str(user), full_email)

    def test_machineuser_str(self):
        system = 'Zodiac'
        user = MachineUser.objects.create(system_name="Zodiac")
        self.assertEqual(str(user), system)
