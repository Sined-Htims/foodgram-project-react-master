from django.core.validators import RegexValidator


class HexValidator(RegexValidator):
    regex = r'^#([A-Fa-f0-9]{6})$'
    message = ("Введенное вами значение не является цветовым HEX-кодом")
