from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.views.decorators.cache import cache_page

from .models import User, Post, Group, Comment, Follow
from .utils import get_page_context
from .forms import PostForm, CommentForm


@cache_page(20, key_prefix='index_page')
def index(request):
    index = True
    return render(
        request,
        'posts/index.html',
        {
            'index': index,
            **get_page_context(
                Post.objects.select_related('group').all(), request
            )
        }
    )


def group_posts(request, slug):
    group = get_object_or_404(Group, slug=slug)
    return render(
        request,
        'posts/group_list.html',
        {'group': group, **get_page_context(group.posts.all(), request)}
    )


def profile(request, username):
    author = get_object_or_404(User, username=username)
    user = request.user
    following = author.following.filter(
        user=request.user.id,
        author=author
    ).exists()
    return render(
        request,
        'posts/profile.html',
        {
            'user': user,
            'author': author,
            'following': following,
            **get_page_context(author.posts.all(), request)}
    )


def post_detail(request, post_id):
    post = get_object_or_404(Post, id=post_id)
    form = CommentForm(request.POST or None)
    comments = Comment.objects.all()
    return render(
        request,
        'posts/post_detail.html',
        {
            'post': post,
            'user': request.user,
            'form': form,
            'comments': comments,
        }
    )


@login_required
def post_create(request):
    form = PostForm(request.POST or None, files=request.FILES or None)
    if request.method == 'POST':
        if form.is_valid():
            form = form.save(commit=False)
            form.author = request.user
            form.save()
            return redirect('posts:profile', form.author)
    return render(
        request,
        'posts/create_post.html',
        {'form': form, 'is_edit': False}
    )


@login_required
def post_edit(request, post_id):
    post = get_object_or_404(Post, pk=post_id)
    if request.user != post.author:
        return redirect('posts:post_detail', post_id)
    form = PostForm(
        request.POST or None,
        instance=post,
        files=request.FILES or None,
    )
    if form.is_valid():
        form.save()
        return redirect('posts:post_detail', post_id)
    return render(
        request,
        'posts/create_post.html',
        {'post': post, 'form': form, 'is_edit': True}
    )


@login_required
def add_comment(request, post_id):
    post = get_object_or_404(Post, pk=post_id)
    form = CommentForm(request.POST or None)
    if form.is_valid():
        comment = form.save(commit=False)
        comment.author = request.user
        comment.post = post
        comment.save()
    return redirect('posts:post_detail', post_id=post_id)


@login_required
def follow_index(request):
    user = request.user
    authors = user.follower.values('author')
    posts = Post.objects.filter(author__in=authors)
    follow = True
    return render(
        request,
        'posts/index.html',
        {'follow': follow, **get_page_context(posts.all(), request)}
    )


@login_required
def profile_follow(request, username):
    author = get_object_or_404(User, username=username)
    user = request.user
    if author != user:
        Follow.objects.get_or_create(user=user, author=author)
    return redirect('posts:profile', username=username)


@login_required
def profile_unfollow(request, username):
    user = request.user
    Follow.objects.filter(user=user, author__username=username).delete()
    return redirect('posts:profile', username=username)
