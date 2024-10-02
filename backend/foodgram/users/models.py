from django.conf import settings
from django.contrib.auth.models import AbstractUser
from django.contrib.auth.validators import UnicodeUsernameValidator
from django.core.validators import MinLengthValidator
from django.db import models
from django.db.models import CheckConstraint, F, UniqueConstraint, Q

from users.validators import username_validator


class Subscription(models.Model):
    '''Модель подписок.'''
    subscriber = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='user_subscriptions',
        verbose_name='Фанат',
        help_text='Кто подписывается'
    )
    subscribed_to = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='user_subscribers',
        verbose_name='Кумир',
        help_text='На кого подписывается'
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Дата подписки',
        help_text='Когда подписался'
    )

    class Meta:
        ordering = ('-id',)
        verbose_name = 'Подписка'
        verbose_name_plural = 'Подписки'
        constraints = [
            CheckConstraint(
                check=~Q(subscriber=F('subscribed_to')),
                name='prevent_self_subscription',
            ),
            UniqueConstraint(
                fields=['subscriber', 'subscribed_to'],
                name='prevent_duplicate_subscription'
            )
        ]

    def __str__(self):
        return f'"{self.subscriber}", подписался на "{self.subscribed_to}"'


class CustomUser(AbstractUser):
    '''Кастомная модель пользователя.'''
    email = models.EmailField(
        verbose_name='Адрес электронной почты',
        max_length=settings.MAX_LENGTH_EMAIL,
        unique=True
    )
    username = models.CharField(
        verbose_name='Имя пользователя',
        max_length=settings.MAX_LENGTH_USERNAME,
        unique=True,
        validators=[UnicodeUsernameValidator(), username_validator],
    )
    password = models.CharField(
        verbose_name='Пароль',
        max_length=settings.MAX_LENGTH_PASSWORD,
        validators=[MinLengthValidator(settings.MIN_LENGTH_PASSWORD)]
    )
    first_name = models.CharField(
        verbose_name='Имя',
        max_length=settings.MAX_LENGTH_FIRST_NAME
    )
    last_name = models.CharField(
        verbose_name='Фамилия',
        max_length=settings.MAX_LENGTH_LAST_NAME
    )
    subscriptions = models.ManyToManyField(
        'self',
        through='Subscription',
        through_fields=('subscribed_to', 'subscriber'),
        symmetrical=False,
        related_name='following',
        verbose_name='Подписки'
    )

    def subscribe(self, user: 'CustomUser') -> None:
        '''Подписка.'''
        Subscription.objects.create(subscriber=self, subscribed_to=user)

    def unsubscribe(self, user: 'CustomUser') -> None:
        '''Отписка.'''
        Subscription.objects.filter(
            subscriber=self, subscribed_to=user
        ).delete()

    def is_subscribed(self, user: 'CustomUser') -> bool:
        '''Проверка: подписан ли текущий пользователь на другого.'''
        return Subscription.objects.filter(
            subscriber=self, subscribed_to=user
        ).exists()

    def subscribed_to(self, user: 'CustomUser') -> bool:
        '''Проверка: подписан ли пользователь на текущего пользователя.'''
        return Subscription.objects.filter(
            subscriber=user, subscribed_to=self
        ).exists()

    class Meta:
        ordering = ('-id',)
        verbose_name = 'Пользователь'
        verbose_name_plural = 'Пользователи'

    def __str__(self):
        return self.username
