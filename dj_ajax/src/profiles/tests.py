import io
import tempfile

from django.conf import settings
from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse
from PIL import Image

from .models import Profile

AJAX_HEADERS = {'HTTP_X_REQUESTED_WITH': 'XMLHttpRequest'}


def make_test_avatar(filename='avatar.png'):
    """Return an in-memory PNG upload for profile avatar tests."""
    buffer = io.BytesIO()
    Image.new('RGB', (12, 12), color='teal').save(buffer, format='PNG')
    return SimpleUploadedFile(filename, buffer.getvalue(), content_type='image/png')


class ProfileSignalAndModelTests(TestCase):
    """Verify automatic profile creation and string representation."""

    def test_profile_created_automatically_on_user_creation(self):
        user = User.objects.create_user(username='charlie', password='TestPassword123!')
        profile = Profile.objects.get(user=user)
        self.assertEqual(str(profile), 'profile of the user charlie')


class ProfileViewsTests(TestCase):
    """Verify my_profile_view auth, HTTP methods, and profile updates."""

    def setUp(self):
        self.user = User.objects.create_user(username='dana', password='TestPassword123!')
        self.profile = Profile.objects.get(user=self.user)
        self.url = reverse('profiles:my-profile')

    def test_unauthenticated_redirects_to_login(self):
        res = self.client.get(self.url)
        self.assertEqual(res.status_code, 302)
        self.assertIn(settings.LOGIN_URL, res.url)

    def test_disallowed_http_method_returns_405(self):
        self.client.force_login(self.user)
        res = self.client.delete(self.url)
        self.assertEqual(res.status_code, 405)

    def test_get_profile_renders_template(self):
        self.client.force_login(self.user)
        res = self.client.get(self.url)
        self.assertEqual(res.status_code, 200)
        self.assertTemplateUsed(res, 'profiles/main.html')

    def test_ajax_post_updates_bio_and_avatar(self):
        self.client.force_login(self.user)
        with tempfile.TemporaryDirectory() as media_dir:
            with override_settings(MEDIA_ROOT=media_dir):
                res = self.client.post(
                    self.url,
                    data={'bio': 'Updated bio text', 'avatar': make_test_avatar()},
                    **AJAX_HEADERS,
                )
                self.assertEqual(res.status_code, 200)
                payload = res.json()
                self.assertEqual(payload['bio'], 'Updated bio text')
                self.assertEqual(payload['user'], 'dana')
                self.assertIn('avatars/', payload['avatar'])
                self.profile.refresh_from_db()
                self.assertEqual(self.profile.bio, 'Updated bio text')

    def test_non_ajax_post_renders_template(self):
        self.client.force_login(self.user)
        res = self.client.post(self.url, data={'bio': 'Non-AJAX bio'})
        self.assertEqual(res.status_code, 200)
        self.assertTemplateUsed(res, 'profiles/main.html')
