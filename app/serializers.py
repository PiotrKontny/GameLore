from rest_framework import serializers
from .models import CustomUser
from .models import Games
from .models import GamePlots
from .models import UserHistory
from .models import ChatBot


# Serializer od użytkownika
class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomUser  # Powiązanie z modelem od klienta
        fields = ["id", "username", 'email', 'user_password', 'date_joined']  # Pola do serializacji z bazy danych
        extra_kwargs = {
            "user_password": {"write_only": True}}  # Hasło dostępne tylko do zapisu niewidoczne w odpowiedzi

    # Tworzenie użytkownika
    def create(self, validated_data):
        user = CustomUser.objects.create_user(
            username=validated_data['login'],
            user_password=validated_data['user_password'],
            email=validated_data['email'],
        )
        return user


class GamesSerializer(serializers.ModelSerializer):
    class Meta:
        model = Games
        fields = ['id', 'title', 'release_year', 'genre', 'cover_image', 'created_at']


class GamePlotsSerializer(serializers.ModelSerializer):
    game_id = GamesSerializer()

    class Meta:
        model = GamePlots
        fields = ['id', 'game_id', 'full_plot', 'summary', 'source_url', 'created_at']


# Serializer od tabeli COMPOSITION
class UserHistorySerializer(serializers.ModelSerializer):
    user_id = UserSerializer()
    game_id = GamesSerializer()

    class Meta:
        model = UserHistory
        fields = ['id', 'user_id', 'game_id', 'viewed_at']


# Serializer od tabeli ORDERS
class ChatBotSerializer(serializers.ModelSerializer):
    user_id = UserSerializer()
    game_id = GamesSerializer()

    class Meta:
        model = ChatBot
        fields = ['id', 'user_id', 'game_id', 'question', 'answer', 'created_at']
