from django.urls import path
from . import views

app_name = 'recommendations'

urlpatterns = [
    path('', views.recommendation_form, name='recommendation_form'),
    path('result/', views.recommendation_result, name='recommendation_result')
]