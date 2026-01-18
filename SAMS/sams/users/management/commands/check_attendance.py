from django.core.management.base import BaseCommand
from django.core.mail import send_mail
from django.conf import settings
from users.models import Student, Attendance

class Command(BaseCommand):
    help = "Check attendance and notify parents if below threshold"

    def handle(self, *args, **kwargs):
        threshold = 75  # attendance percentage limit
        for student in Student.objects.all():
            total = Attendance.objects.filter(student=student).count()
            present = Attendance.objects.filter(student=student, status=1).count()

            if total > 0:
                percentage = present / total * 100
                if percentage < threshold and student.parent and student.parent.email:
                    subject = f"Low Attendance Alert for {student.user.full_name}"
                    message = f"""
Dear {student.parent.full_name},

Your child {student.user.full_name} (Roll: {student.roll_no})
has an attendance percentage of {percentage:.2f}%, which is below the required {threshold}% threshold.

Please take necessary steps to improve attendance.

Regards,
School Administration
"""
                    send_mail(subject, message, settings.DEFAULT_FROM_EMAIL, [student.parent.email])
                    self.stdout.write(self.style.SUCCESS(
                        f"Email sent to {student.parent.email} for {student.user.full_name}"
                    ))

