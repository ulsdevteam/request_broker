from django.test import TestCase

from .models import MachineUser, User

# Create your tests here.

class TestPackage(TestCase):

    def setUp(self):
        pass

    def test_user_methods(self):
        user = User.objects.create(
            email="pgalligan@rockarch.org",
            first_name="Patrick",
            last_name="Galligan",
            username="pgalligan")
        name = 'Patrick Galligan'
        full_email = 'Patrick Galligan <pgalligan@rockarch.org>'
        self.assertEqual(user.full_name, name)
        self.assertEqual(str(user), full_email)

    def test_machineuser_str(self):
        system = 'Zodiac'
        user = MachineUser.objects.create(
            system_name="Zodiac",
            host_location='http://127.0.0.1',
            api_key='key')
        self.assertEqual(str(user), system)
