from django.urls import path
from . import views

app_name = "workbench"
urlpatterns = [
    path("", views.index, name="index"),
    path("api/source/", views.source, name="source"),
    path("api/action/", views.action, name="action"),
]
