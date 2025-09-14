from django.utils.timezone import now
import os
from django.contrib.auth.base_user import BaseUserManager, AbstractBaseUser
from django.db import models
from django.contrib.auth.models import AbstractUser, PermissionsMixin
from django.core.validators import RegexValidator, FileExtensionValidator

class CustomUserManager(BaseUserManager):
    def create_user(self, username, password=None, **extra_fields):  # Tworzenie nowego użytkownika
        if not username:  # Sprawdzanie, czy podano login
            raise ValueError('The Username field must be set')

        # Ustawienie domyślnych wartości dla opcjonalnych pól
        extra_fields.setdefault('email', 'Unknown')
        extra_fields.setdefault('date_joined', now())
        user = self.model(login=username, **extra_fields)  # Tworzenie instancji modelu użytkownika
        user.set_password(password)  # Haszowanie hasła
        user.save(using=self._db)  # Zapis użytkownika w bazie danych
        return user

# Model Klienta
class CustomUser(AbstractBaseUser):
    id = models.BigAutoField(primary_key=True, db_column='id')
    username = models.CharField(max_length=100, unique=True, null=False, default="username")
    email = models.CharField(max_length=255, unique=True, null=False, db_column='email')
    user_password = models.CharField(max_length=255, null=False, db_column='user_password')
    date_joined = models.DateTimeField(default=now, db_column='date_joined')

    USERNAME_FIELD = 'username'
    REQUIRED_FIELDS = []  # Żadne inne pola nie są wymagane przy tworzeniu użytkownika

    objects = CustomUserManager()

    class Meta:
        db_table = 'users'

    def __str__(self):
        return self.username

class Games(models.Model):
    id = models.BigAutoField(primary_key=True, db_column='id')
    title = models.CharField(max_length=255, null=False, d_column='title')
    release_year = models.IntegerField(db_column='release_year')
    genre = models.CharField(max_length=100, d_column='genre')
    cover_image = models.ImageField(upload_to='covers/', db_column='cover_image')
    created_at = models.DateTimeField(auto_now_add=True, db_column='created_at')

    class Meta:
        db_table = 'games'

class GamePlots(models.Model):
    id = models.BigAutoField(primary_key=True, db_column='id')
    game_id = models.ForeignKey(Games, on_delete=models.CASCADE, related_name="plots", db_column='game_id')
    full_plot = models.TextField(db_column='full_plot')
    summary = models.TextField(db_column='summary')
    source_url = models.CharField(max_length=500, d_column='source_url')
    created_at = models.DateTimeField(auto_now_add=True, db_column='created_at')

    class Meta:
        db_table = 'gameplots'

class UserHistory(models.Model):
    id = models.BigAutoField(primary_key=True, db_column='id')
    user_id = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name="user_histories", db_column='user_id')
    game_id = models.ForeignKey(Games, on_delete=models.CASCADE, related_name="user_games_history", db_column='game_id')
    viewed_at = models.DateTimeField(auto_now_add=True, db_column='viewed_at')

    class Meta:
        db_table = 'userhistory'

class ChatBot(models.Model):
    id = models.BigAutoField(primary_key=True, db_column='id')
    user_id = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name="chatbot_user", db_column='user_id')
    game_id = models.ForeignKey(Games, on_delete=models.CASCADE, related_name="chatbot_user_games", db_column='game_id')
    question = models.TextField(null=False, db_column='question')
    answer = models.TextField(null=False, db_column='answer')
    created_at = models.DateTimeField(auto_now_add=True, db_column='created_at')

    class Meta:
        db_table = 'chatbot'
