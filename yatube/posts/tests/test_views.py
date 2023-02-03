import shutil
import tempfile

from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.cache import cache
from django.conf import settings
from django.contrib.auth import get_user_model
from django.test import Client, TestCase, override_settings
from django.urls import reverse
from django import forms

from ..models import Post, Group, Comment, Follow

User = get_user_model()

TEMP_MEDIA_ROOT = tempfile.mkdtemp(dir=settings.BASE_DIR)


@override_settings(MEDIA_ROOT=TEMP_MEDIA_ROOT)
class PostPagesTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.author = User.objects.create_user(username='author')
        cls.user = User.objects.create_user(username='bob')
        cls.group = Group.objects.create(
            title='Тестовая группа',
            slug='test-slug',
            description='Тестовое описание',
        )
        small_gif = (
            b'\x47\x49\x46\x38\x39\x61\x02\x00'
            b'\x01\x00\x80\x00\x00\x00\x00\x00'
            b'\xFF\xFF\xFF\x21\xF9\x04\x00\x00'
            b'\x00\x00\x00\x2C\x00\x00\x00\x00'
            b'\x02\x00\x01\x00\x00\x02\x02\x0C'
            b'\x0A\x00\x3B'
        )
        uploaded = SimpleUploadedFile(
            name='small.gif',
            content=small_gif,
            content_type='image/gif'
        )
        cls.post = Post.objects.create(
            author=cls.author,
            text='Тестовый пост',
            group=cls.group,
            image=uploaded,
        )
        cls.comment = Comment.objects.create(
            post=cls.post,
            author=cls.author,
            text='Тестовый коммент'
        )

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(TEMP_MEDIA_ROOT, ignore_errors=True)

    def setUp(self):
        cache.clear()
        self.author_client = Client()
        self.author_client.force_login(self.author)
        self.authorized_client = Client()
        self.authorized_client.force_login(self.user)
        self.guest_client = Client()

    def test_pages_uses_correct_template(self):
        """URL-адрес использует соответствующий шаблон."""
        templates_pages_names = {
            reverse('posts:index'): 'posts/index.html',
            reverse(
                'posts:group_list', kwargs={'slug': 'test-slug'}
            ): 'posts/group_list.html',
            reverse(
                'posts:profile', kwargs={'username': 'author'}
            ): 'posts/profile.html',
            reverse(
                'posts:post_detail', kwargs={'post_id': '1'}
            ): 'posts/post_detail.html',
            reverse('posts:post_create'): 'posts/create_post.html',
            reverse(
                'posts:post_edit', kwargs={'post_id': '1'}
            ): 'posts/create_post.html',
        }
        for reverse_name, template in templates_pages_names.items():
            with self.subTest(reverse_name=reverse_name):
                response = self.author_client.get(reverse_name)
                self.assertTemplateUsed(response, template)

    def test_home_page_show_correct_context(self):
        """Шаблон index сформирован с правильным контекстом."""
        response = self.author_client.get(reverse('posts:index'))
        first_object = response.context['page_obj'][0]
        self.assertEqual(first_object.text, self.post.text)
        self.assertEqual(
            first_object.author.username, self.post.author.username
        )
        self.assertEqual(first_object.group.title, self.post.group.title)
        self.assertEqual(first_object.image, self.post.image)

    def test_group_list_page_show_correct_context(self):
        """Шаблон group_list сформирован с правильным контекстом."""
        response = self.author_client.get(
            reverse('posts:group_list', kwargs={'slug': 'test-slug'})
        )
        first_object = response.context['page_obj'][0]
        second_object = response.context['group']
        self.assertEqual(first_object.text, self.post.text)
        self.assertEqual(
            first_object.author.username, self.post.author.username
        )
        self.assertEqual(second_object.title, self.group.title)
        self.assertEqual(second_object.slug, self.group.slug)
        self.assertEqual(second_object.description, self.group.description)
        self.assertEqual(first_object.image, self.post.image)

    def test_profile_page_show_correct_context(self):
        """Шаблон profile сформирован с правильным контекстом."""
        response = self.author_client.get(
            reverse('posts:profile', kwargs={'username': 'author'})
        )
        obj = response.context['page_obj'][0]
        author = response.context['author']
        self.assertEqual(obj.text, self.post.text)
        self.assertEqual(obj.author.username, self.post.author.username)
        self.assertEqual(obj.group.title, self.post.group.title)
        self.assertEqual(author.username, self.post.author.username)
        self.assertEqual(obj.image, self.post.image)

    def test_post_detail_show_correct_context(self):
        """Шаблон post_detail сформирован с правильным контекстом."""
        response = self.author_client.get(
            reverse('posts:post_detail', kwargs={'post_id': '1'})
        )
        form_field = response.context.get('form').fields.get('text')
        self.assertIsInstance(form_field, forms.fields.CharField)

        obj = response.context['post']
        user = response.context['user']
        comment = response.context['comments'][0]
        self.assertEqual(obj.text, self.post.text)
        self.assertEqual(obj.author.username, self.post.author.username)
        self.assertEqual(obj.group.title, self.post.group.title)
        self.assertEqual(user.username, self.post.author.username)
        self.assertEqual(obj.image, self.post.image)
        self.assertEqual(comment.post, self.post)
        self.assertEqual(comment.author, self.comment.author)
        self.assertEqual(comment.text, self.comment.text)

    def test_post_create_show_correct_context(self):
        """Шаблон post_create сформирован с правильным контекстом."""
        response = self.author_client.get(reverse('posts:post_create'))
        form_fields = {
            'text': forms.fields.CharField,
            'group': forms.fields.ChoiceField,
        }
        for value, expected in form_fields.items():
            with self.subTest(value=value):
                form_field = response.context.get('form').fields.get(value)
                self.assertIsInstance(form_field, expected)
        self.assertFalse(response.context['is_edit'])

    def test_post_edit_show_correct_context(self):
        """Шаблон post_create сформирован с правильным контекстом."""
        response = self.author_client.get(
            reverse('posts:post_edit', kwargs={'post_id': '1'})
        )
        form_fields = {
            'text': forms.fields.CharField,
            'group': forms.fields.ChoiceField,
        }
        for value, expected in form_fields.items():
            with self.subTest(value=value):
                form_field = response.context.get('form').fields.get(value)
                self.assertIsInstance(form_field, expected)
        obj = response.context['post']
        self.assertEqual(obj.text, self.post.text)
        self.assertEqual(obj.author.username, self.post.author.username)
        self.assertEqual(obj.group.title, self.post.group.title)
        self.assertTrue(response.context['is_edit'])

    def test_home_page_cache(self):
        """Проверка кэша для домашней страницы."""
        old_response = self.author_client.get(reverse('posts:index'))
        old_posts = old_response.content
        Post.objects.create(
            text='Тестовй пост',
            author=self.author,
            group=self.group,
        )
        response = self.author_client.get(reverse('posts:index'))
        posts = response.content
        self.assertEqual(old_posts, posts)
        cache.clear()
        new_response = self.author_client.get(reverse('posts:index'))
        new_posts = new_response.content
        self.assertNotEqual(old_posts, new_posts)

    def test_authorized_user_can_follow(self):
        """Авторизованный пользователь может подписываться."""
        followers_count = Follow.objects.count()
        self.authorized_client.get(
            reverse('posts:profile_follow', kwargs={'username': 'author'})
        )
        self.assertEqual(Follow.objects.count(), followers_count + 1)

    def test_authorized_user_can_unfollow(self):
        """Авторизованный пользователь может отписываться."""
        followers_count = Follow.objects.count()
        self.authorized_client.get(
            reverse('posts:profile_unfollow', kwargs={'username': 'author'})
        )
        self.assertEqual(Follow.objects.count(), followers_count)

    def test_follow_page(self):
        """Новая запись пользователя появляется у тех, кто подписан."""
        first_user = Client()
        first_user.force_login(User.objects.create_user(username='first'))

        second_user = Client()
        second_user.force_login(User.objects.create_user(username='second'))

        post_creator_obj = User.objects.create_user(username='creator')
        post_creator = Client()
        post_creator.force_login(post_creator_obj)
        # первый пользователь подписывается на creator
        first_user.get(
            reverse('posts:profile_follow', kwargs={'username': 'creator'})
        )
        # creator создает пост
        Post.objects.create(
            text='Текст',
            author=post_creator_obj,
        )
        first_user_response = first_user.get(reverse('posts:follow_index'))
        # пост пользователя creator появляется на странице подписок перового
        self.assertEqual(
            first_user_response.context['page_obj'].paginator.count, 1
        )
        second_user_response = second_user.get(reverse('posts:follow_index'))
        # этот пост не появляется на странице подписок второго
        self.assertEqual(
            second_user_response.context['page_obj'].paginator.count, 0
        )
        # если пользователь отписывается, пост у него пропадает
        first_user.get(
            reverse('posts:profile_unfollow', kwargs={'username': 'creator'})
        )
        first_user_response = first_user.get(reverse('posts:follow_index'))
        self.assertEqual(
            first_user_response.context['page_obj'].paginator.count, 0
        )


class PaginatorViewsTest(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.author = User.objects.create_user(username='author')
        cls.group = Group.objects.create(
            title='Тестовая группа',
            slug='test-slug',
            description='Тестовое описание',
        )
        posts = []
        for text in range(13):
            posts.append(
                Post(
                    text=f'Текст {text + 1}',
                    author=cls.author,
                    group=cls.group
                )
            )
        Post.objects.bulk_create(posts)

    def setUp(self):
        cache.clear()
        self.author_client = Client()
        self.author_client.force_login(self.author)
        self.namespace_list = [
            reverse('posts:index'),
            reverse(
                'posts:group_list', kwargs={'slug': 'test-slug'}
            ),
            reverse(
                'posts:profile', kwargs={'username': 'author'}
            ),
        ]

    def test_first_page_contains_ten_records(self):
        """Превая страница паджинатора работает правильно."""
        for name in self.namespace_list:
            response = self.author_client.get(name)
            self.assertEqual(len(response.context['page_obj']), 10)

    def test_second_page_contains_three_records(self):
        """Вторая страница паджинатора работает правильно."""
        for name in self.namespace_list:
            response = self.author_client.get(name + '?page=2')
            self.assertEqual(len(response.context['page_obj']), 3)
