from django.core.exceptions import ValidationError


def username_validator(username: str) -> None:
    if username.lower() in {
        'me', 'set_password', 'subscribe', 'subscriptions'
    }:
        raise ValidationError('Данное имя нельзя использовать')
