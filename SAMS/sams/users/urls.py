from django.urls import path
from . import views

urlpatterns = [
    # 🏠 Home & Authentication
    path('', views.home, name='home'),
    path('login/', views.custom_login, name='login'),
    path('logout/', views.custom_logout, name='logout'),

    # 📊 Dashboards
    path('teacher/dashboard/', views.teacher_dashboard, name='teacher_dashboard'),
    path('student/dashboard/', views.student_dashboard, name='student_dashboard'),
    path('parent/dashboard/', views.parent_dashboard, name='parent_dashboard'),

    # 📅 Datewise Attendance
    path('parent/datewise/<int:student_id>/', views.student_datewise_attendance, name='datewise_attendance'),
    path('student/datewise/<int:student_id>/', views.student_datewise_attendance, name='student_datewise_attendance'),

    # 📧 Parent Notification (Teacher only)
    path('teacher/notify/<int:student_id>/<int:class_id>/', views.notify_parent_view, name='notify_parent'),

    # 📋 Attendance Management
    path('take-attendance/<int:class_id>/<str:date>/', views.take_attendance, name='take_attendance'),
    path('attendance-summary/<int:class_id>/', views.attendance_summary, name='attendance_summary'),

    # ✏️ Attendance Edit (Teacher only)
    path('edit-attendance/<int:student_id>/<int:class_id>/', views.edit_attendance, name='edit_attendance'),

    # 🔑 OTP-based Password Reset
    path('forgot-password/', views.forgot_password_view, name='forgot_password'),
    path('verify-otp/', views.verify_otp_view, name='verify_otp'),
    path('reset-password/', views.reset_password_view, name='reset_password'),

    # 📄 PDF Downloads (Parent Dashboard)
    path(
        'parent-dashboard/<int:student_id>/class/<int:class_id>/pdf/',
        views.download_class_summary_pdf,
        name='download_class_summary_pdf'
    ),
    path(
        'parent-dashboard/<int:student_id>/all-classes/pdf/',
        views.download_all_class_summary_pdf,
        name='download_all_class_summary_pdf'
    ),
]
