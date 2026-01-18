from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.db import models

# 🔹 Custom User Manager
class UserManager(BaseUserManager):
    def create_user(self, email, full_name, password=None, **extra_fields):
        if not email:
            raise ValueError("The Email field must be set")
        email = self.normalize_email(email)
        user = self.model(email=email, full_name=full_name, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, full_name, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('role', 'ADMIN')  # default role for superuser

        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser must have is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser must have is_superuser=True.')

        return self.create_user(email, full_name, password, **extra_fields)


# 🔹 Custom User Model
class User(AbstractUser):
    username = None
    email = models.EmailField(unique=True)
    full_name = models.CharField(max_length=150)

    ROLE_CHOICES = [
        ('ADMIN', 'Admin'),
        ('TEACHER', 'Teacher'),
        ('STUDENT', 'Student'),
        ('PARENT', 'Parent'),
    ]
    
    role = models.CharField(max_length=10, choices=ROLE_CHOICES)
    phone = models.CharField(max_length=20, blank=True)
    address = models.TextField(blank=True)
    department = models.CharField(max_length=100, blank=True)
    profile_pic = models.ImageField(upload_to='profile_pics/', blank=True, null=True)

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['full_name']

    objects = UserManager()

    def __str__(self):
        return f"{self.full_name} ({self.role})"


# 🔹 TimeSlot Model (Bangladeshi fixed slots)
class TimeSlot(models.Model):
    start_time = models.TimeField()
    end_time = models.TimeField()

    def __str__(self):
        return f"{self.start_time.strftime('%H:%M')} - {self.end_time.strftime('%H:%M')}"


# 🔹 Class Model (Teacher assigned per class)
class Class(models.Model):
    code = models.CharField(max_length=20)   # e.g. CSC 469
    title = models.CharField(max_length=100) # e.g. Data Mining
    semester = models.CharField(max_length=50) # e.g. Fall 2026
    year = models.IntegerField(null=True, blank=True)
    time_slot = models.ForeignKey(TimeSlot, on_delete=models.CASCADE)
    teacher = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        limit_choices_to={'role': 'TEACHER'},
        related_name='assigned_classes',
        null=True, blank=True
    )

    def __str__(self):
        return f"{self.code} ({self.semester} {self.year if self.year else ''})"


# 🔹 Student Model (Many-to-Many with Class)
class Student(models.Model):
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        limit_choices_to={'role': 'STUDENT'}
    )
    roll_no = models.CharField(max_length=20)

    # ✅ Multiple classes allowed
    classes = models.ManyToManyField(Class, related_name="students")

    # Parent link (optional, can be null)
    parent = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        limit_choices_to={'role': 'PARENT'},
        related_name='children'
    )

    semester = models.CharField(max_length=20, blank=True)
    year = models.IntegerField(null=True, blank=True)

    def __str__(self):
        return f"{self.roll_no} - {self.user.full_name}"


# 🔹 Attendance Model
class Attendance(models.Model):
    student = models.ForeignKey(Student, on_delete=models.CASCADE)
    class_obj = models.ForeignKey(Class, on_delete=models.CASCADE, null=True, blank=True)
    date = models.DateField()
    status = models.IntegerField(choices=[(1, 'Present'), (0, 'Absent')])
    marked_by = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        limit_choices_to={'role': 'TEACHER'}
    )
    created_at = models.DateTimeField(auto_now_add=True)
    remarks = models.TextField(blank=True)

    class Meta:
        unique_together = ('student', 'class_obj', 'date')
        ordering = ['-date']

    def __str__(self):
        return f"{self.student.user.full_name} - {self.class_obj.code if self.class_obj else 'N/A'} - {self.date} - {self.get_status_display()}"


# 🔹 Notification Model (Teacher → Parent alerts)
class Notification(models.Model):
    parent = models.ForeignKey(User, on_delete=models.CASCADE, related_name="notifications")
    student = models.ForeignKey(Student, on_delete=models.CASCADE)
    message = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    is_read = models.BooleanField(default=False)

    def __str__(self):
        return f"Notification for {self.parent.full_name} - {self.student.roll_no}"