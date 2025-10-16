from django.db import models

class Games(models.Model):
    title = models.CharField(max_length=255)
    release_date = models.CharField(max_length=255, null=True, blank=True)
    genre = models.CharField(max_length=500, blank=True, null=True)
    studio = models.TextField(null=True, blank=True)
    score = models.DecimalField(max_digits=3, decimal_places=1, null=True, blank=True)
    cover_image = models.CharField(max_length=500, null=True, blank=True)  # ścieżka względna, np. game_icons/x.jpg
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'games'

    def __str__(self):
        return self.title


class GamePlot(models.Model):
    game = models.ForeignKey(Games, on_delete=models.CASCADE)
    full_plot = models.TextField()
    summary = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'gameplots'
