from django.utils.timezone import now
import os
from django.utils import timezone
from django.contrib.auth.base_user import BaseUserManager
from django.db import models
from django.contrib.auth.models import AbstractUser, PermissionsMixin
from django.core.validators import RegexValidator, FileExtensionValidator
from django.contrib.auth.hashers import make_password, check_password


class UserManager(BaseUserManager):
    def create_user(self, username, email, password=None, **extra_fields):
        if not username:
            raise ValueError("Username is required")
        if not email:
            raise ValueError("Email is required")
        email = self.normalize_email(email)
        user = self.model(username=username, email=email, **extra_fields)
        if password:
            user.password = make_password(password)  # zapisze do kolumny user_password
        else:
            user.password = make_password(self.make_random_password())
        user.save(using=self._db)
        return user

    def create_superuser(self, username, email, password=None, **extra_fields):
        return self.create_user(username, email, password, **extra_fields)


class UserModel(models.Model):
    id = models.AutoField(primary_key=True)
    username = models.CharField(max_length=100, unique=True)
    email = models.EmailField(unique=True)
    password = models.CharField(max_length=128, db_column='user_password')
    date_joined = models.DateTimeField(default=timezone.now)

    objects = UserManager()  # <<< DODANE

    USERNAME_FIELD = "username"
    REQUIRED_FIELDS = ["email"]

    class Meta:
        db_table = "Users"
        managed = False

    def set_password(self, raw_password):
        self.password = make_password(raw_password)

    def check_password(self, raw_password):
        return check_password(raw_password, self.password)

    @property
    def is_active(self):
        return True
    @property
    def is_authenticated(self):
        return True
    @property
    def is_anonymous(self):
        return False

    def __str__(self): return self.username

class Games(models.Model):
    id = models.BigAutoField(primary_key=True, db_column='id')
    title = models.CharField(max_length=255, null=False, db_column='title')
    # On MobyGames release dates are expressed like "October 1, 2025 on PlayStation 5" and there could be more release
    # dates for different platforms, thus the usage of Varchar2(255)
    release_date = models.CharField(max_length=255, db_column='release_year')
    genre = models.CharField(max_length=100, db_column='genre')
    studio = models.TextField(db_column='studio')
    score = models.DecimalField(max_digits=3, decimal_places=1, db_column='score')
    cover_image = models.ImageField(upload_to='covers/', db_column='cover_image')
    created_at = models.DateTimeField(auto_now_add=True, db_column='created_at')

    class Meta:
        db_table = 'Games'

class GamePlots(models.Model):
    id = models.BigAutoField(primary_key=True, db_column='id')
    game_id = models.ForeignKey(Games, on_delete=models.CASCADE, related_name="plots", db_column='game_id')
    full_plot = models.TextField(db_column='full_plot')
    summary = models.TextField(db_column='summary')
    created_at = models.DateTimeField(auto_now_add=True, db_column='created_at')

    class Meta:
        db_table = 'GamePlots'

class UserHistory(models.Model):
    id = models.BigAutoField(primary_key=True, db_column='id')
    user_id = models.ForeignKey(UserModel, on_delete=models.CASCADE, related_name="user_histories", db_column='user_id')
    game_id = models.ForeignKey(Games, on_delete=models.CASCADE, related_name="user_games_history", db_column='game_id')
    viewed_at = models.DateTimeField(auto_now_add=True, db_column='viewed_at')

    class Meta:
        db_table = 'UserHistory'

class ChatBot(models.Model):
    id = models.BigAutoField(primary_key=True, db_column='id')
    user_id = models.ForeignKey(UserModel, on_delete=models.CASCADE, related_name="chatbot_user", db_column='user_id')
    game_id = models.ForeignKey(Games, on_delete=models.CASCADE, related_name="chatbot_user_games", db_column='game_id')
    question = models.TextField(null=False, db_column='question')
    answer = models.TextField(null=False, db_column='answer')
    created_at = models.DateTimeField(auto_now_add=True, db_column='created_at')

    class Meta:
        db_table = 'ChatBot'
