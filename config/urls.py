from django.conf import settings
from django.contrib import admin
from django.urls import include, path, re_path
from django.views.generic import RedirectView
from django.views.static import serve

urlpatterns = [
    path("", RedirectView.as_view(pattern_name="panel:dashboard", permanent=False)),
    path("panel/", include("panel.urls")),
    path("django-admin/", admin.site.urls),
    # Savol rasmlari (hajm kichik — alohida nginx shart emas; xohlasangiz nginx'ga o'tkazing)
    re_path(r"^media/(?P<path>.*)$", serve, {"document_root": settings.MEDIA_ROOT}),
]
