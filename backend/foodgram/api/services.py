from django.http import HttpResponse
# Для ПДФ
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle
from reportlab.platypus.paragraph import Paragraph


def create_ingredients_pdf(ingredients: dict):
    '''
    Функция для создания и выдачи в ответ, PDF-файла.
    На вход получает словарь с ингредиентами полученные из БД.
    '''
    # Создание PDF-документа
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = 'attachment; filename="shopping_list.pdf"'
    doc = SimpleDocTemplate(response, pagesize=letter)
    elements = []
    # Настройка стилей для Paragraph
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name='Center', alignment=1))
    # Добавление заголовка
    elements.append(Paragraph('Список покупок', styles['Heading1']))
    elements.append(Paragraph(' ', styles['BodyText']))
    # Создание таблицы ингредиентов
    data = [['Ингредиент', 'Система измерения', 'Количество']]
    for (ingredient_name, ingredient_unit), amount in ingredients.items():
        data.append(
            [
                Paragraph(ingredient_name, styles['BodyText']),
                Paragraph(ingredient_unit, styles['BodyText']), amount
            ]
        )
    table = Table(data)
    # Ставил пробелы после запятых у чисел
    table_style = TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 14),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
    ])
    table.setStyle(table_style)
    # Добавление таблицы в элементы PDF
    elements.append(table)
    # Построение и возврат PDF-документа
    doc.build(elements)
    return response
