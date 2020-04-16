import json
import os

from asnake.jsonmodel import wrap_json_object
from django.test import TestCase

from .models import MachineUser, User
from .routines import DeliveryFormats


class TestUsers(TestCase):

    def test_user(self):
        user = User(
            first_name="Patrick",
            last_name="Galligan",
            email="pgalligan@rockarch.org")
        self.assertEqual(user.full_name, "Patrick Galligan")
        self.assertEqual(str(user), "Patrick Galligan <pgalligan@rockarch.org>")

    def test_machineuser(self):
        system = 'Zodiac'
        user = MachineUser(system_name="Zodiac")
        self.assertEqual(str(user), system)

class TestRoutines(TestCase):

    def obj_from_fixture(self, filename, client=None):
        with open(os.path.join("fixtures", filename)) as json_file:
            data = json.load(json_file)
            obj = wrap_json_object(data, client=client)
            return obj

    def test_check_instances(self):
        for fixture, outcome in [
            ("object_all.json", True),
            ("object_mixed.json",True),
            ("object_digital.json", True),
            ("object_microform.json", True),
            ("object_av.json", None),
            ("object_no_instance.json", None)]:
            object = self.obj_from_fixture(fixture)
            result = DeliveryFormats.check_formats(object)
            self.assertEqual(result, outcome)
