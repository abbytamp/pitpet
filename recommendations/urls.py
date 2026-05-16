from django.urls import path
from . import views

app_name = 'recommendations'

urlpatterns = [
    path('', views.recommendation_form, name='recommendation_form'),
    path('start/', views.recommendation_start, name='recommendation_start'),
    path('result/', views.recommendation_result, name='recommendation_result')
]