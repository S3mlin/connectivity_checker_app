from django.urls import path
from main_app import views

urlpatterns = [
    path("users/<email>/", views.my_sites, name="my_sites"),
    path("subscribe/<email>/<site_id>/", views.subscribe, name="subscribe"),
    path("unsubscribe/<email>/<site_id>/", views.unsubscribe, name="unsubscribe"),
    path("search_and_subscribe/<email>/", views.search_and_subscribe, name="search_and_subscribe"),
]