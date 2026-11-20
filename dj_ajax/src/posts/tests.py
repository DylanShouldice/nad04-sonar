import io
import tempfile

from django.conf import settings
from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse
from PIL import Image

from profiles.models import Profile
from .models import Photo, Post

AJAX_HEADERS = {'HTTP_X_REQUESTED_WITH': 'XMLHttpRequest'}


def make_test_image(filename='sample.png'):
    """Return an in-memory PNG upload suitable for ImageField tests."""
    buffer = io.BytesIO()
    Image.new('RGB', (10, 10), color='navy').save(buffer, format='PNG')
    return SimpleUploadedFile(filename, buffer.getvalue(), content_type='image/png')


class SettingsSecurityDefaultsTests(TestCase):
    """Verify insecure development defaults are no longer hardcoded."""

    def test_security_defaults_are_safe(self):
        self.assertFalse(settings.DEBUG)
        self.assertTrue(settings.SECRET_KEY)
        self.assertFalse(settings.SECRET_KEY.startswith('django-insecure-'))
        self.assertNotIn('*', settings.ALLOWED_HOSTS)


class PostModelTests(TestCase):
    """Verify Post and Photo model helpers."""

    def setUp(self):
        self.user = User.objects.create_user(username='author', password='TestPassword123!')
        self.profile = Profile.objects.get(user=self.user)
        self.post = Post.objects.create(
            title='Sample Post',
            body='Sample body content',
            author=self.profile,
        )

    def test_post_str_and_like_count(self):
        self.assertEqual(str(self.post), 'Sample Post')
        self.assertEqual(self.post.like_count, 0)
        self.post.liked.add(self.user)
        self.assertEqual(self.post.like_count, 1)

    def test_post_get_photos_and_photo_str(self):
        with tempfile.TemporaryDirectory() as media_dir:
            with override_settings(MEDIA_ROOT=media_dir):
                photo = Photo.objects.create(post=self.post, image=make_test_image())
                self.assertEqual(list(self.post.get_photos()), [photo])
                self.assertEqual(str(photo), f'Sample Post-{photo.pk}')


class PostViewsTests(TestCase):
    """Verify authentication, HTTP method restrictions, and post view behavior."""

    def setUp(self):
        self.author_user = User.objects.create_user(username='alice', password='TestPassword123!')
        self.other_user = User.objects.create_user(username='bob', password='TestPassword123!')
        self.author_profile = Profile.objects.get(user=self.author_user)
        self.post = Post.objects.create(
            title='First Post',
            body='Django testing body',
            author=self.author_profile,
        )

    def test_unauthenticated_request_redirects_to_login(self):
        response = self.client.get(reverse('posts:main-board'))
        self.assertEqual(response.status_code, 302)
        self.assertIn(settings.LOGIN_URL, response.url)

    def test_http_method_restrictions_return_405(self):
        self.client.force_login(self.author_user)

        get_only_urls = [
            reverse('posts:post-detail', kwargs={'pk': self.post.pk}),
            reverse('posts:posts-data', kwargs={'num_posts': 3}),
            reverse('posts:post-detail-data', kwargs={'pk': self.post.pk}),
            reverse('posts:search-posts'),
        ]
        for url in get_only_urls:
            response = self.client.post(url, **AJAX_HEADERS)
            self.assertEqual(response.status_code, 405, f'Expected 405 for POST {url}')

        post_only_urls = [
            reverse('posts:like-unlike'),
            reverse('posts:like-unlike-via-url', kwargs={'pk': self.post.pk}),
        ]
        for url in post_only_urls:
            response = self.client.get(url, **AJAX_HEADERS)
            self.assertEqual(response.status_code, 405, f'Expected 405 for GET {url}')

        delete_response = self.client.delete(reverse('posts:main-board'))
        self.assertEqual(delete_response.status_code, 405)

    def test_post_list_and_create_get_and_post(self):
        self.client.force_login(self.author_user)

        get_res = self.client.get(reverse('posts:main-board'))
        self.assertEqual(get_res.status_code, 200)
        self.assertTemplateUsed(get_res, 'posts/main.html')

        ajax_res = self.client.post(
            reverse('posts:main-board'),
            data={'title': 'Created Title', 'body': 'Created Body'},
            **AJAX_HEADERS,
        )
        self.assertEqual(ajax_res.status_code, 200)
        payload = ajax_res.json()
        self.assertEqual(payload['title'], 'Created Title')
        self.assertEqual(payload['body'], 'Created Body')
        self.assertEqual(payload['author'], 'alice')
        self.assertTrue(Post.objects.filter(pk=payload['id']).exists())

        non_ajax_res = self.client.post(
            reverse('posts:main-board'),
            data={'title': 'Ignored Non-AJAX', 'body': 'Body'},
        )
        self.assertEqual(non_ajax_res.status_code, 200)
        self.assertTemplateUsed(non_ajax_res, 'posts/main.html')
        self.assertFalse(Post.objects.filter(title='Ignored Non-AJAX').exists())

    def test_post_detail_and_detail_data_views(self):
        self.client.force_login(self.author_user)

        detail_res = self.client.get(reverse('posts:post-detail', kwargs={'pk': self.post.pk}))
        self.assertEqual(detail_res.status_code, 200)
        self.assertTemplateUsed(detail_res, 'posts/detail.html')

        ajax_res = self.client.get(
            reverse('posts:post-detail-data', kwargs={'pk': self.post.pk}),
            **AJAX_HEADERS,
        )
        self.assertEqual(ajax_res.status_code, 200)
        data = ajax_res.json()['data']
        self.assertEqual(data['id'], self.post.pk)
        self.assertEqual(data['title'], 'First Post')
        self.assertEqual(data['author'], 'alice')
        self.assertEqual(data['logged_in'], 'alice')
        self.assertFalse(data['liked'])

        non_ajax_res = self.client.get(
            reverse('posts:post-detail-data', kwargs={'pk': self.post.pk})
        )
        self.assertEqual(non_ajax_res.status_code, 302)

    def test_load_post_data_view_pagination(self):
        self.client.force_login(self.author_user)
        self.post.liked.add(self.author_user)
        Post.objects.create(title='Second Post', body='Body 2', author=self.author_profile)

        res = self.client.get(
            reverse('posts:posts-data', kwargs={'num_posts': 3}),
            **AJAX_HEADERS,
        )
        self.assertEqual(res.status_code, 200)
        body = res.json()
        self.assertEqual(body['size'], 2)
        self.assertEqual(len(body['data']), 2)
        liked_map = {item['title']: item['liked'] for item in body['data']}
        self.assertTrue(liked_map['First Post'])
        self.assertFalse(liked_map['Second Post'])

    def test_like_unlike_post_endpoints(self):
        self.client.force_login(self.author_user)

        like_url = reverse('posts:like-unlike')
        res1 = self.client.post(like_url, data={'pk': self.post.pk}, **AJAX_HEADERS)
        self.assertEqual(res1.status_code, 200)
        self.assertEqual(res1.json(), {'liked': True, 'count': 1})

        res2 = self.client.post(like_url, data={'pk': self.post.pk}, **AJAX_HEADERS)
        self.assertEqual(res2.status_code, 200)
        self.assertEqual(res2.json(), {'liked': False, 'count': 0})

        non_ajax = self.client.post(like_url, data={'pk': self.post.pk})
        self.assertEqual(non_ajax.status_code, 302)

        via_url = reverse('posts:like-unlike-via-url', kwargs={'pk': self.post.pk})
        res3 = self.client.post(via_url, **AJAX_HEADERS)
        self.assertEqual(res3.status_code, 200)
        self.assertEqual(res3.json(), {'liked': True, 'count': 1})

        res4 = self.client.post(via_url, **AJAX_HEADERS)
        self.assertEqual(res4.status_code, 200)
        self.assertEqual(res4.json(), {'liked': False, 'count': 0})

        via_url_non_ajax = self.client.post(via_url)
        self.assertEqual(via_url_non_ajax.status_code, 400)

    def test_update_and_delete_post_permissions_and_actions(self):
        update_url = reverse('posts:post-update', kwargs={'pk': self.post.pk})
        delete_url = reverse('posts:post-delete', kwargs={'pk': self.post.pk})

        self.client.force_login(self.other_user)
        forbidden_update = self.client.post(
            update_url,
            data={'title': 'Hijacked', 'body': 'Nope'},
            **AJAX_HEADERS,
        )
        self.assertEqual(forbidden_update.status_code, 302)
        self.post.refresh_from_db()
        self.assertEqual(self.post.title, 'First Post')

        self.client.force_login(self.author_user)
        missing_res = self.client.post(
            reverse('posts:post-update', kwargs={'pk': 99999}),
            data={'title': 'X', 'body': 'Y'},
            **AJAX_HEADERS,
        )
        self.assertEqual(missing_res.status_code, 404)

        update_res = self.client.post(
            update_url,
            data={'title': 'Updated Title', 'body': 'Updated Body'},
            **AJAX_HEADERS,
        )
        self.assertEqual(update_res.status_code, 200)
        self.assertEqual(
            update_res.json(),
            {'title': 'Updated Title', 'body': 'Updated Body'},
        )

        non_ajax_del = self.client.post(delete_url)
        self.assertEqual(non_ajax_del.status_code, 302)
        self.assertTrue(Post.objects.filter(pk=self.post.pk).exists())

        del_res = self.client.post(delete_url, **AJAX_HEADERS)
        self.assertEqual(del_res.status_code, 200)
        self.assertEqual(del_res.json(), {'msg': 'Post Deleted'})
        self.assertFalse(Post.objects.filter(pk=self.post.pk).exists())

    def test_image_upload_view(self):
        self.client.force_login(self.author_user)
        upload_url = reverse('posts:image-upload')

        get_res = self.client.get(upload_url)
        self.assertEqual(get_res.status_code, 405)

        with tempfile.TemporaryDirectory() as media_dir:
            with override_settings(MEDIA_ROOT=media_dir):
                post_res = self.client.post(
                    upload_url,
                    data={'post_id': self.post.pk, 'file': make_test_image()},
                )
                self.assertEqual(post_res.status_code, 200)
                self.assertEqual(
                    post_res.json(),
                    {'message': 'Image uploaded successfully!'},
                )
                self.assertEqual(Photo.objects.filter(post=self.post).count(), 1)

    def test_image_upload_rejects_non_author_idor(self):
        self.client.force_login(self.other_user)
        upload_url = reverse('posts:image-upload')

        with tempfile.TemporaryDirectory() as media_dir:
            with override_settings(MEDIA_ROOT=media_dir):
                res = self.client.post(
                    upload_url,
                    data={'post_id': self.post.pk, 'file': make_test_image()},
                )
                self.assertEqual(res.status_code, 403)
                self.assertEqual(Photo.objects.filter(post=self.post).count(), 0)

    def test_image_upload_missing_file_or_unknown_post(self):
        self.client.force_login(self.author_user)
        upload_url = reverse('posts:image-upload')

        missing_file = self.client.post(upload_url, data={'post_id': self.post.pk})
        self.assertEqual(missing_file.status_code, 400)

        with tempfile.TemporaryDirectory() as media_dir:
            with override_settings(MEDIA_ROOT=media_dir):
                unknown_post = self.client.post(
                    upload_url,
                    data={'post_id': 99999, 'file': make_test_image()},
                )
                self.assertEqual(unknown_post.status_code, 404)

    def test_unauthenticated_update_and_delete_redirect_to_login(self):
        update_res = self.client.post(
            reverse('posts:post-update', kwargs={'pk': self.post.pk}),
            data={'title': 'Anon', 'body': 'Body'},
        )
        self.assertEqual(update_res.status_code, 302)
        self.assertIn(settings.LOGIN_URL, update_res.url)

        delete_res = self.client.post(
            reverse('posts:post-delete', kwargs={'pk': self.post.pk}),
        )
        self.assertEqual(delete_res.status_code, 302)
        self.assertIn(settings.LOGIN_URL, delete_res.url)

    def test_update_and_delete_disallow_get_with_405(self):
        self.client.force_login(self.author_user)
        update_get = self.client.get(reverse('posts:post-update', kwargs={'pk': self.post.pk}))
        delete_get = self.client.get(reverse('posts:post-delete', kwargs={'pk': self.post.pk}))
        self.assertEqual(update_get.status_code, 405)
        self.assertEqual(delete_get.status_code, 405)

    def test_non_ajax_update_post_redirects_safely(self):
        self.client.force_login(self.author_user)
        res = self.client.post(
            reverse('posts:post-update', kwargs={'pk': self.post.pk}),
            data={'title': 'Non-AJAX', 'body': 'Ignored'},
        )
        self.assertEqual(res.status_code, 302)
        self.post.refresh_from_db()
        self.assertEqual(self.post.title, 'First Post')

    def test_search_posts_view(self):
        self.client.force_login(self.author_user)
        search_url = reverse('posts:search-posts')

        non_ajax = self.client.get(search_url, {'q': 'First'})
        self.assertEqual(non_ajax.status_code, 400)

        empty_res = self.client.get(search_url, {'q': '   '}, **AJAX_HEADERS)
        self.assertEqual(empty_res.status_code, 200)
        self.assertEqual(empty_res.json(), {'data': []})

        match_res = self.client.get(search_url, {'q': 'Django'}, **AJAX_HEADERS)
        self.assertEqual(match_res.status_code, 200)
        results = match_res.json()['data']
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]['id'], self.post.pk)
