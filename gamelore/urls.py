from django.contrib import admin
from django.urls import path, include, re_path
from django.conf import settings
from django.conf.urls.static import static
from app.views import react_index

urlpatterns = [
    path('admin/', admin.site.urls),
    path('app/', include('app.urls')),
    path('', react_index, name='home'),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

# Fallback — WSZYSTKO (oprócz /admin/ i /media/) → React
re_path(r'^(?!media/).*$', react_index)
