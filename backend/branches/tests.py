from branches.models import Branch, Subject
from rest_framework.test import APITestCase


class SubjectApiTests(APITestCase):
	def setUp(self):
		self.branch = Branch.objects.create(name="Main Branch", address="1 Center St", city="Kyiv")

	def test_subject_list_is_paginated(self):
		Subject.objects.create(name="Math", branch=self.branch)
		Subject.objects.create(name="English", branch=self.branch)

		response = self.client.get("/api/v1/subjects/")

		self.assertEqual(response.status_code, 200)
		self.assertIn("results", response.data)
		self.assertEqual(response.data["count"], 2)

	def test_duplicate_subject_name_in_same_branch_is_rejected(self):
		payload = {"name": "Math", "branch_id": self.branch.id}

		first_response = self.client.post("/api/v1/subjects/", payload, format="json")
		second_response = self.client.post("/api/v1/subjects/", payload, format="json")

		self.assertEqual(first_response.status_code, 201)
		self.assertEqual(second_response.status_code, 400)
		self.assertIn("non_field_errors", second_response.data)
