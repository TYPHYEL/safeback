from django.contrib import admin
from .models import Rating


@admin.register(Rating)
class RatingAdmin(admin.ModelAdmin):
    list_display = ('id', 'rater', 'ratee', 'score', 'created_at')
    list_filter = ('score',)
