from django.db import models
from django.db.models import Count, Prefetch
from django.urls import reverse
from django.contrib.auth.models import User
import more_itertools


class TagQuerySet(models.QuerySet):

    def popular(self):
        popular_tags = self.annotate(related_posts_count=Count('posts')).order_by("-related_posts_count")
        return popular_tags


class PostQuerySet(models.QuerySet):

    def popular(self):
        popular_posts = self.annotate(likes_count=Count('likes', distinct=True)).order_by("-likes_count")
        return popular_posts

    def fetch_with_comments_count(self):
        posts_with_comments = Post.objects.filter(id__in=self).annotate(comments_count=Count('comments'))
        id_comments = dict(posts_with_comments.values_list("id", "comments_count"))
        for post in self:
            post.comments_count = id_comments[post.id]
        return self

    def fresh(self):
        fresh_posts = self.order_by("-published_at")
        return fresh_posts

    def fetch_with_tags(self):
        posts_counts_for_tags = Post.objects.filter(id__in=self).prefetch_related(
            Prefetch("tags",
                     queryset=Tag.objects.annotate(
                         posts_with_tag=Count('posts')
                        )
                     )
        )
        for post in self:
            tags = [post_with_tags.tags for post_with_tags in posts_counts_for_tags if post_with_tags.id == post.id]
            for tag in more_itertools.first(tags).all():
                post.total_tags = {
                    "title": tag.title,
                    "posts_with_tag": tag.posts_with_tag
                }
        return self


class Post(models.Model):
    title = models.CharField('Заголовок', max_length=200)
    text = models.TextField('Текст')
    slug = models.SlugField('Название в виде url', max_length=200)
    image = models.ImageField('Картинка')
    published_at = models.DateTimeField('Дата и время публикации')
    author = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        verbose_name='Автор',
        limit_choices_to={'is_staff': True},
        related_name="post"
    )
    likes = models.ManyToManyField(
        User,
        related_name='liked_posts',
        verbose_name='Кто лайкнул',
        blank=True)
    tags = models.ManyToManyField(
        'Tag',
        related_name='posts',
        verbose_name='Теги')
    objects = PostQuerySet.as_manager()

    def __str__(self):
        return self.title

    def get_absolute_url(self):
        return reverse('post_detail', args={'slug': self.slug})

    class Meta:
        ordering = ['-published_at']
        verbose_name = 'пост'
        verbose_name_plural = 'посты'


class Tag(models.Model):
    title = models.CharField('Тег', max_length=20, unique=True)
    objects = TagQuerySet.as_manager()

    def __str__(self):
        return self.title

    def clean(self):
        self.title = self.title.lower()

    def get_absolute_url(self):
        return reverse('tag_filter', args={'tag_title': self.slug})

    class Meta:
        ordering = ['title']
        verbose_name = 'тег'
        verbose_name_plural = 'теги'


class Comment(models.Model):
    post = models.ForeignKey(
        'Post',
        on_delete=models.CASCADE,
        verbose_name='Пост, к которому написан',
        related_name='comments')
    author = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        verbose_name='Автор',
        related_name='comments'
    )

    text = models.TextField('Текст комментария')
    published_at = models.DateTimeField('Дата и время публикации')

    def __str__(self):
        return f'{self.author.username} under {self.post.title}'

    class Meta:
        ordering = ['published_at']
        verbose_name = 'комментарий'
        verbose_name_plural = 'комментарии'
