from django.contrib import admin
from django.urls import path, include
from django.views.generic import RedirectView
from django.conf import settings
from django.conf.urls.static import static as static_media


urlpatterns = [
    # Dashboard principal (raíz de /spia/)
    path('spia/', include('dashboard.urls')),

    # Admin
    path('spia/admin/', admin.site.urls),

    # Apps
    path('spia/empleados/', include('empleados.urls')),
    path('spia/solicitudes/', include('solicitudes.urls')),
    path('spia/movimientos/', include('movimientos.urls')),

    # Redirección raíz: / → /spia/
    path('', RedirectView.as_view(url='/spia/', permanent=False)),
]

if settings.DEBUG:
    urlpatterns += static_media(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)