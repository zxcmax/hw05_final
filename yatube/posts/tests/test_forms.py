import shutil
import tempfile

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.conf import settings
from django.test import Client, TestCase, override_settings
from django.urls import reverse

from ..forms import PostForm, CommentForm
from ..models import Post, Group, Comment

User = get_user_model()

TEMP_MEDIA_ROOT = tempfile.mkdtemp(dir=settings.BASE_DIR)


@override_settings(MEDIA_ROOT=TEMP_MEDIA_ROOT)
class PostCreateFormTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.author = User.objects.create_user(username='author')
        cls.group = Group.objects.create(
            title='Тестовая группа',
            slug='test-slug',
            description='Тестовое описание',
        )
        cls.post = Post.objects.create(
            author=cls.author,
            text='Тестовый пост',
            group=cls.group
        )
        cls.form = PostForm()

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(TEMP_MEDIA_ROOT, ignore_errors=True)

    def setUp(self):
        self.author_client = Client()
        self.author_client.force_login(self.author)

    def test_post_create(self):
        """Валидная форма создает запись."""
        posts_count = Post.objects.count()
        form_data = {
            'text': 'Тестовый текст',
            'group': self.group.id
        }
        response = self.author_client.post(
            reverse('posts:post_create'),
            data=form_data,
            follow=True
        )
        # Проверяем, сработал ли редирект
        self.assertRedirects(
            response, reverse('posts:profile', kwargs={'username': 'author'})
        )
        # Проверяем, увеличилось ли число постов
        self.assertEqual(Post.objects.count(), posts_count + 1)
        self.assertTrue(
            Post.objects.filter(
                text=form_data['text'],
            ).exists()
        )
        new_post = Post.objects.last()
        self.assertEqual(new_post.author, self.author)
        self.assertEqual(new_post.group, self.group)

    def test_post_edit(self):
        """Валидная форма изменяет запись."""
        second_group = Group.objects.create(
            title='Тестовая группа 2',
            slug='second-test-slug',
            description='Тестовое описание 2',
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
        form_data = {
            'text': 'Тестовый текст 2',
            'group': second_group.id,
            'image': uploaded,
        }
        response = self.author_client.post(
            reverse('posts:post_edit', kwargs={'post_id': '1'}),
            data=form_data,
            follow=True
        )
        # Проверяем, сработал ли редирект
        self.assertRedirects(
            response, reverse('posts:post_detail', kwargs={'post_id': '1'})
        )
        self.assertTrue(
            Post.objects.filter(
                text=form_data['text'],
                group=form_data['group'],
                image='posts/small.gif',
            ).exists()
        )
        # Проверяем, что пост исчез со страницы старой группы
        old_group_response = self.author_client.get(
            reverse('posts:group_list', args=(self.group.slug,))
        )
        self.assertEqual(
            old_group_response.context['page_obj'].paginator.count, 0
        )
        # Проверяем, что пост появился на странице новой группы
        new_group_response = self.author_client.get(
            reverse('posts:group_list', args=(second_group.slug,))
        )
        self.assertEqual(
            new_group_response.context['page_obj'].paginator.count, 1
        )


class CommentFormTest(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.author = User.objects.create_user(username='author')
        cls.group = Group.objects.create(
            title='Тестовая группа',
            slug='test-slug',
            description='Тестовое описание',
        )
        cls.post = Post.objects.create(
            author=cls.author,
            text='Тестовый пост',
            group=cls.group
        )
        cls.form = CommentForm()

    def setUp(self):
        self.author_client = Client()
        self.author_client.force_login(self.author)

    def test_comment_create(self):
        """Валидная форма создает комментарий."""
        comments_count = Comment.objects.count()
        form_data = {
            'post': self.post,
            'author': self.author,
            'text': 'Тестовый текст',
        }
        response = self.author_client.post(
            reverse('posts:add_comment', kwargs={'post_id': self.post.id}),
            data=form_data,
            follow=True
        )
        # Проверяем, сработал ли редирект
        self.assertRedirects(
            response, reverse('posts:post_detail', kwargs={'post_id': self.post.id})
        )
        # Проверяем, увеличилось ли число комментариев
        self.assertEqual(Comment.objects.count(), comments_count + 1)
        self.assertTrue(
            Comment.objects.filter(
                post=form_data['post'],
                author=form_data['author'],
                text=form_data['text'],
            ).exists()
        )
        new_comment = Comment.objects.last()
        self.assertEqual(new_comment.post, self.post)
        self.assertEqual(new_comment.author, self.author)
