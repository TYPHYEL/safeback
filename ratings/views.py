from rest_framework import viewsets, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.pagination import PageNumberPagination
from django.db import models
from django.contrib.auth import get_user_model
from django.shortcuts import get_object_or_404
from .models import Rating
from .serializers import RatingSerializer
from .utils import calculate_trust_score as detailed_calculate_trust_score

User = get_user_model()


class SmallResultsSetPagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = 'page_size'
    max_page_size = 100


def calculate_trust_score(ratee_user):
    ratings_received = Rating.objects.filter(ratee=ratee_user)

    if not ratings_received.exists():
        return {
            'trust_score': 3.0,
            'level': 'Moyen',
            'ratings_count': 0,
            'average_rating': 3.0,
        }

    avg_rating = ratings_received.aggregate(models.Avg('score'))['score__avg'] or 3.0
    trust_score = min(5.0, max(0.0, avg_rating))

    if trust_score >= 4.5:
        level = 'Excellent'
    elif trust_score >= 4.0:
        level = 'Très bon'
    elif trust_score >= 3.5:
        level = 'Bon'
    elif trust_score >= 3.0:
        level = 'Moyen'
    elif trust_score >= 2.0:
        level = 'Faible'
    else:
        level = 'Très faible'

    return {
        'trust_score': round(trust_score, 2),
        'level': level,
        'ratings_count': ratings_received.count(),
        'average_rating': round(avg_rating, 2),
    }


class RatingViewSet(viewsets.ModelViewSet):
    queryset = Rating.objects.all()
    serializer_class = RatingSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = SmallResultsSetPagination

    def get_queryset(self):
        user = self.request.user
        if user.is_staff:
            return self.queryset
        return self.queryset.filter(rater=user) | self.queryset.filter(ratee=user)

    def perform_create(self, serializer):
        serializer.save(rater=self.request.user)

    def create(self, request, *args, **kwargs):
        ratee = request.data.get('ratee')
        trip = request.data.get('trip')
        if ratee and trip:
            exists = Rating.objects.filter(rater=request.user, ratee_id=ratee, trip_id=trip).exists()
            if exists:
                return Response({'detail': 'You have already rated this user for this trip.'}, status=status.HTTP_400_BAD_REQUEST)
        return super().create(request, *args, **kwargs)

    @action(detail=False, methods=['get'])
    def my_score(self, request):
        """Calculate trust score for current user with detailed breakdown"""
        result = detailed_calculate_trust_score(request.user)
        return Response(result)

    @action(detail=False, methods=['get'], url_path='user/(?P<pk>[^/.]+)', url_name='user_score')
    def user_score(self, request, pk=None):
        """Retrieve detailed trust score and paginated ratings for a specific user by ID"""
        ratee_user = get_object_or_404(User, pk=pk)

        trust_info = detailed_calculate_trust_score(ratee_user)

        recent_ratings = Rating.objects.filter(
            ratee=ratee_user
        ).order_by('-created_at')

        paginator = self.pagination_class()
        page = paginator.paginate_queryset(recent_ratings, request)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            paginated_response = paginator.get_paginated_response(serializer.data)
            paginated_data = paginated_response.data
        else:
            serializer = self.get_serializer(recent_ratings, many=True)
            paginated_data = {
                'count': recent_ratings.count(),
                'next': None,
                'previous': None,
                'results': serializer.data,
            }

        response_data = {
            'trust_score': trust_info['trust_score'],
            'level': trust_info['level'],
            'breakdown': trust_info['breakdown'],
            'ratings_count': trust_info['ratings_count'],
            'verified': trust_info['verified'],
            'account_days': trust_info['account_days'],
            'incident_free_trips': trust_info['incident_free_trips'],
            'count': paginated_data.get('count'),
            'next': paginated_data.get('next'),
            'previous': paginated_data.get('previous'),
            'results': paginated_data.get('results', []),
        }
        return Response(response_data, status=status.HTTP_200_OK)
