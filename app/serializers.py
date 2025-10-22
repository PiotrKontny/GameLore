from rest_framework import serializers
from .models import UserModel, Games, GamePlots, UserHistory, ChatBot


class UserSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)

    class Meta:
        model = UserModel
        fields = ["id", "username", "email", "password"]

    def create(self, validated_data):
        return UserModel.objects.create_user(
            username=validated_data["username"],
            email=validated_data["email"],
            password=validated_data["password"],
        )


class GamesSerializer(serializers.ModelSerializer):
    class Meta:
        model = Games
        fields = ['id', 'title', 'release_date', 'genre', 'studio', 'score', 'cover_image', 'created_at']


class GamePlotsSerializer(serializers.ModelSerializer):
    game_id = GamesSerializer(read_only=True)

    class Meta:
        model = GamePlots
        fields = ['id', 'game_id', 'full_plot', 'summary', 'created_at']


class UserHistorySerializer(serializers.ModelSerializer):
    user_id = UserSerializer()
    game_id = GamesSerializer()

    class Meta:
        model = UserHistory
        fields = ['id', 'user_id', 'game_id', 'viewed_at']


class ChatBotSerializer(serializers.ModelSerializer):
    user_id = UserSerializer()
    game_id = GamesSerializer()

    class Meta:
        model = ChatBot
        fields = ['id', 'user_id', 'game_id', 'question', 'answer', 'created_at']
