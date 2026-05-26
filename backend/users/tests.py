from rest_framework import status
from rest_framework.test import APITestCase

from branches.models import Branch
from .models import User


class UserProfileTests(APITestCase):
	def setUp(self):
		self.branch = Branch.objects.create(name="Main", address="1", city="Kyiv")
		self.admin = User.objects.create_user(
			phone="+38000000010",
			password="secret",
			first_name="Admin",
			last_name="User",
			role="ADMIN",
			branch=self.branch,
		)
		self.teacher = User.objects.create_user(
			phone="+38000000011",
			password="secret",
			first_name="Teach",
			last_name="Er",
			role="TEACHER",
			branch=self.branch,
		)

	def test_user_me_requires_auth(self):
		res = self.client.get("/api/v1/users/me/")
		self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)

	def test_user_me_returns_profile(self):
		self.client.force_authenticate(user=self.teacher)
		res = self.client.get("/api/v1/users/me/")
		self.assertEqual(res.status_code, status.HTTP_200_OK)
		self.assertEqual(res.data["id"], self.teacher.id)
		self.assertEqual(res.data["role"], "TEACHER")
		self.assertIn("branches", res.data)

	def test_auth_me_alias_returns_profile(self):
		self.client.force_authenticate(user=self.teacher)
		res = self.client.get("/api/v1/auth/me/")
		self.assertEqual(res.status_code, status.HTTP_200_OK)
		self.assertEqual(res.data["id"], self.teacher.id)

	def test_users_list_is_admin_only(self):
		self.client.force_authenticate(user=self.teacher)
		res = self.client.get("/api/v1/users/")
		self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)
