from django.db import migrations

class Migration(migrations.Migration):

    dependencies = [
        ('app', '0002_alter_userhistory_options'),  # zostaw dokładnie taki, jaki masz u siebie
    ]

    operations = [
        # Informujemy Django, że pola już istnieją – żadnych zmian w bazie
    ]
