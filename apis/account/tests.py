from typing import Any, Sequence

import factory
from django.test import TestCase
from rest_framework.test import APIClient, APITestCase

import storages.mysql.models.account
from apis.account import models

client = APIClient()


class ProfileFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = storages.mysql.models.account.Profile

    # username = factory.Faker("user_name")
    # phone_number = factory.Faker('phone_number')


# model test
class ProfileTest(TestCase):
    serialized_rollback = True

    def setUp(self) -> None:
        pass

    def test_login(self):
        login_data = {"phone": "18059247212", "password": "18059247212"}
        print(ProfileFactory.build().__dict__)
        print(ProfileFactory.create(**login_data))
        print(ProfileFactory.stub().__dict__)
        # response = client.post(path="/auth/login/", data=login_data)
        # print(response)

    def tearDown(self) -> None:
        pass
