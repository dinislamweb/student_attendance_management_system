from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from users import views  # ✅ তোমার users app এর views import করো

urlpatterns = [
    # 🛠️ Django admin panel
    path('admin/', admin.site.urls),

    # 👥 Include users app routes
    path('', include('users.urls')),

    # 👨‍👩‍👧 Parent Dashboard
    path('parent/dashboard/', views.parent_dashboard, name='parent_dashboard'),

    # 📄 PDF download routes
    path('parent/<int:student_id>/download/all/', views.download_all_class_summary_pdf, name='download_all_class_summary_pdf'),
    path('parent/<int:student_id>/download/class/<int:class_id>/', views.download_class_summary_pdf, name='download_class_summary_pdf'),
]

# 📂 Media serve (development only)
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

