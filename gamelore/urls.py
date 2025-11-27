from django.contrib import admin
from django.urls import path, include, re_path
from django.conf import settings
from django.conf.urls.static import static
from app.views import react_index
import os

urlpatterns = [
    path('admin/', admin.site.urls),
    path('app/', include('app.urls')),
    path('', react_index, name='home'),
    re_path(r'^(?!media/|static/).*$', react_index),
]

urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
urlpatterns += static(
    settings.STATIC_URL,
    document_root=os.path.join(settings.BASE_DIR, 'frontend', 'static', 'frontend')
)
