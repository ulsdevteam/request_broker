from django.test import TestCase

from .models import __str__, full_name

# Create your tests here.

class TestPackage(TestCase):

    def setUp(self):
        pass

    def test_full_name(self):
        name = 'Patrick Galligan'
        self.assertEqual(name, full_name('Patrick', 'Galligan'))

    def test___str__(self):
        pass
