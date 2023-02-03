from django.db import models
from django.contrib.auth import get_user_model

from core.models import CreatedModel

User = get_user_model()

SYMBOLS_IN_TEXT = 15


class Post(models.Model):
    text = models.TextField(
        verbose_name='Текст поста',
        help_text='Напишите текст поста',
    )
    pub_date = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Дата публикации'
    )
    author = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='posts',
        verbose_name='Автор'
    )
    group = models.ForeignKey(
        'Group',
        blank=True,
        null=True,
        on_delete=models.SET_NULL,
        related_name='posts',
        verbose_name='Группа',
        help_text='Выберите группу, к которой будет относиться пост',
    )
    image = models.ImageField(
        'Картинка',
        upload_to='posts/',
        blank=True
    )

    class Meta:
        ordering = ['-pub_date', ]
        verbose_name = 'Пост'
        verbose_name_plural = 'Посты'

    def __str__(self):
        return self.text[:SYMBOLS_IN_TEXT]


class Group(models.Model):
    title = models.CharField(max_length=200, verbose_name='Название')
    slug = models.SlugField(unique=True)
    description = models.TextField(verbose_name='Описание')

    def __str__(self):
        return self.title


class Comment(CreatedModel):
    post = models.ForeignKey(
        'Post',
        on_delete=models.CASCADE,
        related_name='comments',
        verbose_name='Пост'
    )
    author = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='comments',
        verbose_name='Автор'
    )
    text = models.TextField(
        verbose_name='Текст Комментария',
        help_text='Напишите текст комментария',
    )

    class Meta:
        ordering = ['-created', ]

    def __str__(self):
        return (f'Автор: {self.author}, Пост: {self.post}'
                f' текст: {self.text[:SYMBOLS_IN_TEXT]}')


class Follow(models.Model):
    user = models.ForeignKey(
        User,
        related_name='follower',
        verbose_name='Подписчик',
        on_delete=models.CASCADE,
    )
    author = models.ForeignKey(
        User,
        related_name='following',
        verbose_name='Автор',
        on_delete=models.CASCADE,
    )

    def __str__(self):
        return f'{self.user} подписан на {self.author}'
