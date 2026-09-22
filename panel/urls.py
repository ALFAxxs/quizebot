from django.contrib.auth import views as auth_views
from django.urls import path

from . import views

app_name = "panel"

urlpatterns = [
    path("login/", views.LoginView.as_view(), name="login"),
    path("logout/", auth_views.LogoutView.as_view(next_page="panel:login"), name="logout"),
    path("", views.dashboard, name="dashboard"),

    path("packages/", views.package_list, name="package_list"),
    path("packages/new/", views.package_form, name="package_add"),
    path("packages/<int:pk>/", views.package_detail, name="package_detail"),
    path("packages/<int:pk>/edit/", views.package_form, name="package_edit"),
    path("packages/<int:pk>/toggle/", views.package_toggle, name="package_toggle"),
    path("packages/<int:pk>/delete/", views.package_delete, name="package_delete"),
    path("packages/<int:pk>/duplicate/", views.package_duplicate, name="package_duplicate"),

    path("packages/<int:package_pk>/parts/new/", views.part_form, name="part_add"),
    path("parts/<int:pk>/", views.part_detail, name="part_detail"),
    path("parts/<int:pk>/edit/", views.part_form, name="part_edit"),
    path("parts/<int:pk>/delete/", views.part_delete, name="part_delete"),
    path("parts/<int:pk>/move/<str:direction>/", views.part_move, name="part_move"),

    path("parts/<int:part_pk>/questions/new/", views.question_form, name="question_add"),
    path("questions/<int:pk>/edit/", views.question_form, name="question_edit"),
    path("questions/<int:pk>/delete/", views.question_delete, name="question_delete"),

    path("users/", views.user_list, name="user_list"),

    path("results/", views.result_list, name="result_list"),
    path("results/<int:pk>/", views.result_detail, name="result_detail"),
    path("results/<int:pk>/delete/", views.result_delete, name="result_delete"),
]
