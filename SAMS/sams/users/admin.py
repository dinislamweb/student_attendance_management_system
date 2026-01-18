from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin
from .models import User, Student, Attendance, Class, TimeSlot

# 🔹 Admin panel branding
admin.site.site_header = "SAMS Admin Panel"
admin.site.site_title = "SAMS Admin"
admin.site.index_title = "Welcome to SAMS Dashboard"


# 🔹 Custom User Admin
@admin.register(User)
class UserAdmin(DjangoUserAdmin):
    list_display = ('full_name', 'email', 'role', 'phone', 'department', 'is_staff', 'is_active')
    list_filter = ('role', 'department', 'is_staff', 'is_active')
    search_fields = ('full_name', 'email')

    fieldsets = (
        (None, {'fields': ('full_name', 'email', 'password')}),
        ('Personal info', {'fields': ('phone', 'address', 'department', 'profile_pic')}),
        ('Roles', {'fields': ('role',)}),
        ('Permissions', {'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')}),
        ('Important dates', {'fields': ('last_login', 'date_joined')}),
    )

    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': (
                'full_name', 'email', 'role', 'phone', 'address',
                'department', 'profile_pic', 'password1', 'password2'
            ),
        }),
    )

    ordering = ('email',)


# 🔹 Student Admin
@admin.register(Student)
class StudentAdmin(admin.ModelAdmin):
    list_display = ('roll_no', 'user', 'semester', 'year', 'parent')
    list_filter = ('semester', 'year')
    search_fields = ('roll_no', 'user__full_name', 'parent__full_name')
    filter_horizontal = ('classes',)   # ✅ multiple class select করা যাবে


# 🔹 Class Admin (teacher fixed per class)
@admin.register(Class)
class ClassAdmin(admin.ModelAdmin):
    list_display = ('code', 'title', 'semester', 'year', 'time_slot', 'teacher')  # ✅ teacher দেখাবে
    list_filter = ('semester', 'year', 'time_slot', 'teacher')
    search_fields = ('code', 'title', 'semester', 'teacher__full_name')
    autocomplete_fields = ['teacher']  # ✅ শুধু teacher select করা যাবে

    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        # ✅ শুধু TEACHER role‑এর users দেখাবে
        form.base_fields['teacher'].queryset = User.objects.filter(role='TEACHER')
        return form


# 🔹 TimeSlot Admin
@admin.register(TimeSlot)
class TimeSlotAdmin(admin.ModelAdmin):
    list_display = ('start_time', 'end_time')
    search_fields = ('start_time', 'end_time')


# 🔹 Attendance Admin
@admin.register(Attendance)
class AttendanceAdmin(admin.ModelAdmin):
    list_display = ('student', 'class_obj', 'date', 'status', 'marked_by', 'created_at', 'remarks')
    list_filter = ('class_obj', 'date', 'status', 'marked_by')
    search_fields = ('student__user__full_name', 'student__roll_no', 'remarks')
    date_hierarchy = 'date'
    ordering = ('-date',)

