from rest_framework import serializers
from .models import Games, GamePlot

class GameSerializer(serializers.ModelSerializer):
    class Meta:
        model = Games
        fields = ['id', 'title', 'release_date', 'genre', 'studio', 'score', 'cover_image', 'created_at']

class GamePlotSerializer(serializers.ModelSerializer):
    game = GameSerializer(read_only=True)
    class Meta:
        model = GamePlot
        fields = ['id', 'game', 'full_plot', 'summary', 'created_at']
