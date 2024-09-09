from django.contrib import admin

from users.models import CustomUser, Subscription


class SubscriptionInline(admin.TabularInline):
    '''Позволяет оформить подписку на другого пользователя(Можно это убрать)'''
    model = Subscription
    fk_name = 'subscriber'
    extra = 1


class CustomUserAdmin(admin.ModelAdmin):
    '''
    Поиск, добавление промежуточной таблицы и отображение,
    для модели "Пользователи" в админке
    '''
    inlines = [SubscriptionInline]
    list_display = ('username', 'email', 'first_name', 'last_name')
    search_fields = ('username', 'email')


admin.site.register(CustomUser, CustomUserAdmin)


class SubscriptionAdmin(admin.ModelAdmin):
    '''Поиск и отображение для модели "Подписки" в админке'''
    list_display = ('__str__', 'subscriber', 'subscribed_to')
    search_fields = ('subscriber__username', 'subscribed_to__username')


admin.site.register(Subscription, SubscriptionAdmin)
