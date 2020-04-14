import json
import os

from asnake.aspace import ASpace
from asnake.jsonmodel import JSONModelObject, wrap_json_object
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
            ("object_mixed.json", "/repositories/2/top_containers/191156"),
            ("object_digital.json"),
            ("object_microform.json"),
            ("object_no_instance.json"),
            ("object_av.json")]:
            archival_object = self.obj_from_fixture(fixture)
            result = DeliveryFormats.check_instances(archival_object)
            self.assertEqual(result, outcome)
