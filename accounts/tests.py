from django.test import TestCase
from django.urls import reverse

from .models import User


class LogoutCacheControlTests(TestCase):
	def setUp(self):
		self.user = User.objects.create(
			username='customer@example.com',
			full_name='Customer One',
			phone_number='08123456789',
			password='password123',
			role='customer',
		)

	def test_authenticated_pages_disable_browser_caching(self):
		logged_in = self.client.login(username='customer@example.com', password='password123')
		self.assertTrue(logged_in)

		response = self.client.get(reverse('customer_dashboard'))

		self.assertEqual(response.status_code, 200)
		self.assertEqual(response['Cache-Control'], 'no-store, no-cache, must-revalidate, max-age=0')
		self.assertEqual(response['Pragma'], 'no-cache')
		self.assertEqual(response['Expires'], '0')
		self.assertIn('pageshow', response.content.decode())

	def test_logout_redirects_and_invalidates_session(self):
		self.client.login(username='customer@example.com', password='password123')

		response = self.client.get(reverse('logout'))

		self.assertRedirects(response, reverse('login'))
		protected_response = self.client.get(reverse('customer_dashboard'))
		self.assertRedirects(protected_response, f"{reverse('login')}?next={reverse('customer_dashboard')}")
