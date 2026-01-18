import random
from datetime import datetime
from collections import defaultdict

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout, get_user_model
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.mail import send_mail
from django.core.cache import cache
from django.http import HttpResponse
from django.conf import settings

from reportlab.pdfgen import canvas

from .models import Student, Attendance, Class, TimeSlot, Notification


User = get_user_model()

# 🔹 Home Page
def home(request):
    return render(request, 'home.html')

from .models import User   
# Customer_login
def custom_login(request):
    if request.method == 'POST':
        email = request.POST.get('email', '').strip()
        password = request.POST.get('password', '').strip()

        try:
            user_obj = User.objects.get(email=email)
        except User.DoesNotExist:
            messages.add_message(request, messages.ERROR, "Invalid email ❌", extra_tags="email_error")
            return render(request, 'login.html')

        user = authenticate(request, email=email, password=password)
        if user is not None:
            login(request, user)
            role = getattr(user, 'role', None)
            if role == 'TEACHER':
                return redirect('teacher_dashboard')
            elif role == 'STUDENT':
                return redirect('student_dashboard')
            elif role == 'PARENT':
                return redirect('parent_dashboard')
            elif role == 'ADMIN':
                return redirect('/admin/')
            else:
                messages.error(request, 'Role not set or invalid.')
                return redirect('login')
        else:
            messages.add_message(request, messages.ERROR, "Invalid password ❌", extra_tags="password_error")
            return render(request, 'login.html')

    return render(request, 'login.html')

# 🔹 Logout
def custom_logout(request):
    logout(request)
    messages.success(request, "You have been logged out.")
    return redirect('login')

# 🔹 Forgot Password → Send OTP
def forgot_password_view(request):
    if request.method == 'POST':
        email = request.POST.get('email')
        try:
            user = User.objects.get(email=email)
            otp = str(random.randint(100000, 999999))
            cache.set(f"otp_{email}", otp, timeout=300)  # 5 min expiry
            send_mail(
                subject="SAMS Password Reset OTP",
                message=f"Your OTP is {otp}. It will expire in 5 minutes.",
                from_email="noreply@sams.com",
                recipient_list=[email],
            )
            request.session['reset_email'] = email
            messages.success(request, "OTP sent to your email.")
            return redirect('verify_otp')
        except User.DoesNotExist:
            messages.error(request, "No user found with this email.")
    return render(request, 'forgot_password.html')

# 🔹 Verify OTP
def verify_otp_view(request):
    email = request.session.get('reset_email')
    if not email:
        return redirect('forgot_password')

    if request.method == 'POST':
        entered_otp = request.POST.get('otp')
        saved_otp = cache.get(f"otp_{email}")
        if saved_otp and entered_otp == saved_otp:
            return redirect('reset_password')
        else:
            messages.error(request, "Invalid or expired OTP.")
    return render(request, 'verify_otp.html')

# 🔹 Reset Password
def reset_password_view(request):
    email = request.session.get('reset_email')
    if not email:
        return redirect('forgot_password')

    if request.method == 'POST':
        new_password = request.POST.get('new_password')
        confirm_password = request.POST.get('confirm_password')
        if new_password == confirm_password:
            try:
                user = User.objects.get(email=email)
                user.set_password(new_password)
                user.save()
                cache.delete(f"otp_{email}")
                del request.session['reset_email']
                messages.success(request, "Password reset successful. You can now login.")
                return redirect('login')
            except User.DoesNotExist:
                messages.error(request, "User not found.")
        else:
            messages.error(request, "Passwords do not match.")
    return render(request, 'reset_password.html')


@login_required
def teacher_dashboard(request):
    if request.user.role != 'TEACHER':
        messages.error(request, "Only teachers can access the dashboard.")
        return redirect('login')

    teacher = request.user  

    classes = Class.objects.all()

    time_slots = TimeSlot.objects.all()

    selected_class = request.POST.get('class_obj', '')
    selected_date = request.POST.get('date', '')
    selected_time_slot = request.POST.get('time_slot', '')

    if request.method == 'POST' and 'select_class' in request.POST:
        return redirect(
            'take_attendance',
            class_id=selected_class,
            date=selected_date
        )

    elif request.method == 'POST' and 'show_summary' in request.POST:
        return redirect(
            'attendance_summary',
            class_id=selected_class
        )

    return render(request, 'teacher_dashboard.html', {
        'teacher': teacher,   
        'classes': classes,
        'time_slots': time_slots,
        'selected_class': selected_class,
        'selected_date': selected_date,
        'selected_time_slot': selected_time_slot,
    })



# 🔹 Take Attendance Page
@login_required
def take_attendance(request, class_id, date, time_slot_id=None):
    
    if request.user.role != 'TEACHER':
        messages.error(request, "Only teachers can take attendance.")
        return redirect('login')

    class_obj = get_object_or_404(Class, id=class_id)

    if class_obj.teacher != request.user:
        messages.error(request, "You are not authorized to take attendance for this class.")
        return redirect('teacher_dashboard')

    try:
        selected_date = datetime.strptime(date, "%Y-%m-%d").date()
    except ValueError:
        messages.error(request, "Invalid date format.")
        return redirect('teacher_dashboard')

    time_slot = None
    if time_slot_id:
        time_slot = get_object_or_404(TimeSlot, id=time_slot_id)

    students = Student.objects.filter(classes=class_obj)

    records = Attendance.objects.filter(
        class_obj=class_obj,
        date=selected_date
    )
    if time_slot:
        records = records.filter(class_obj__time_slot=time_slot)

    attendance_locked = records.exists()

    if attendance_locked:
        messages.warning(
            request,
            f"Attendance for {class_obj.code} on {selected_date} "
            f"{'('+str(time_slot.start_time)+'-'+str(time_slot.end_time)+')' if time_slot else ''} "
            f"has already been taken."
        )
        return redirect('teacher_dashboard')

    # ✅ Attendance save logic
    if request.method == 'POST':
        for student in students:
            status = request.POST.get(f'status_{student.id}')
            if status is not None:
                Attendance.objects.create(
                    student=student,
                    class_obj=class_obj,   
                    date=selected_date,
                    status=int(status),
                    marked_by=request.user
                )
        messages.success(
            request,
            f"Attendance for {class_obj.code} on {selected_date} "
            f"{'('+str(time_slot.start_time)+'-'+str(time_slot.end_time)+')' if time_slot else ''} "
            f"saved successfully ✅"
        )
        return redirect('teacher_dashboard')

    # ✅ Render template
    return render(request, 'take_attendance.html', {
        'students': students,
        'class_obj': class_obj,
        'date': selected_date,
        'time_slot': time_slot,
        'attendance_locked': attendance_locked
    })


# 🔹 Attendance Summary
@login_required
def attendance_summary(request, class_id):

    if request.user.role != 'TEACHER':
        messages.error(request, "Only teachers can view attendance summary.")
        return redirect('login')

    class_obj = get_object_or_404(Class, id=class_id)

    if class_obj.teacher != request.user:
        messages.error(request, "You are not authorized to view attendance for this class.")
        return redirect('teacher_dashboard')

    students = Student.objects.filter(classes=class_obj)

   
    total_classes = Attendance.objects.filter(class_obj=class_obj).values('date').distinct().count()

    summary = []
    for student in students:
        
        student_records = Attendance.objects.filter(student=student, class_obj=class_obj)

        total_present = student_records.filter(status=1).count()
        total_absent = student_records.filter(status=0).count()
        total_attendance = total_present + total_absent

        # ✅ Attendance percentage calculate (course-specific)
        percentage_attendance = (total_attendance > 0) and (total_present / total_attendance * 100) or 0

        summary.append({
            'student': student,
            'present': total_present,
            'absent': total_absent,
            'percentage_attendance': round(percentage_attendance, 2),
            'total_classes': total_classes,
        })

    return render(request, 'attendance_summary.html', {
        'class_obj': class_obj,
        'summary': summary
    })



# 🔹 Edit Attendance
@login_required
def edit_attendance(request, student_id, class_id):
    
    if request.user.role != 'TEACHER':
        messages.error(request, "Only teachers can edit attendance.")
        return redirect('login')

    student = get_object_or_404(Student, id=student_id)
    class_obj = get_object_or_404(Class, id=class_id)

    
    if class_obj.teacher != request.user:
        messages.error(request, "You are not authorized to edit attendance for this class.")
        return redirect('teacher_dashboard')

    records = Attendance.objects.filter(student=student, class_obj=class_obj).order_by('-date')

    if request.method == 'POST':
        record_id = request.POST.get('record_id')
        new_status = request.POST.get('status')

        record = get_object_or_404(Attendance, id=record_id, student=student, class_obj=class_obj)

       
        if record.class_obj.teacher != request.user:
            messages.error(request, "You are not authorized to update this attendance record.")
            return redirect('teacher_dashboard')

        record.status = int(new_status)
        record.marked_by = request.user
        record.save()

        messages.success(request, f"Attendance updated successfully for {student.user.full_name} in {class_obj.code}!")
        return redirect('edit_attendance', student_id=student.id, class_id=class_obj.id)

    return render(request, 'edit_attendance.html', {
        'student': student,
        'class_obj': class_obj,
        'records': records
    })


@login_required
def student_dashboard(request):
    try:
        
        student = Student.objects.get(user=request.user)

        attendance_records = Attendance.objects.filter(student=student) \
            .select_related('class_obj__time_slot') \
            .order_by('-date')

        class_summary = defaultdict(lambda: {
            'class_obj': None,
            'present': 0,
            'absent': 0,
            'total': 0,
            'percentage': 0
        })

        for record in attendance_records:
            class_obj = record.class_obj
            if not class_obj:
                continue

            class_id = class_obj.id

            if class_summary[class_id]['class_obj'] is None:
                class_summary[class_id]['class_obj'] = class_obj

            if record.status == 1:
                class_summary[class_id]['present'] += 1
            else:
                class_summary[class_id]['absent'] += 1

            class_summary[class_id]['total'] += 1

        
        for summary in class_summary.values():
            if summary['total'] > 0:
                summary['percentage'] = round(summary['present'] / summary['total'] * 100, 2)

        # ✅ Convert to list for easy iteration in template
        class_summary_list = list(class_summary.values())

    except Student.DoesNotExist:
        student = None
        attendance_records = []
        class_summary_list = []

    return render(request, 'student_dashboard.html', {
        'student': student,
        'class_summary': class_summary_list
    })


@login_required
def student_datewise_attendance(request, student_id):
    """
    Show date-wise attendance for a student.
    - If logged in as student: only own attendance.
    - If logged in as parent: can view child's attendance.
    """

    # ✅ Student বের করো (student বা parent অনুযায়ী)
    try:
        # যদি student নিজে login করে
        student = get_object_or_404(Student, id=student_id, user=request.user)
    except:
        # যদি parent login করে
        student = get_object_or_404(Student, id=student_id, parent=request.user)

    # ✅ Attendance records আনো (class + time slot সহ)
    records = Attendance.objects.filter(student=student) \
        .select_related('class_obj__time_slot') \
        .order_by('-date')

    # ✅ Percentage হিসাব করো
    total = records.count()
    present = records.filter(status=1).count()
    percentage = round((present / total * 100), 2) if total > 0 else 0

    return render(request, 'student_datewise_attendance.html', {
        'student': student,
        'records': records,
        'total': total,
        'present': present,
        'absent': total - present,
        'percentage': percentage
    })



@login_required
def notify_parent(request, student_id, class_id):
   
    student = get_object_or_404(Student, id=student_id)
    class_obj = get_object_or_404(Class, id=class_id)

    
    if class_obj.teacher != request.user:
        messages.error(request, "You are not authorized to notify parents for this class.")
        return redirect('teacher_dashboard')

    
    total = Attendance.objects.filter(student=student, class_obj=class_obj).count()
    present = Attendance.objects.filter(student=student, class_obj=class_obj, status=1).count()
    percentage = (present / total * 100) if total > 0 else 0

   
    if request.method == "POST":
        subject = request.POST.get("subject")
        message = request.POST.get("message")

        if percentage < 75 and student.parent and student.parent.email:
            try:
                send_mail(
                    subject,
                    message,
                    settings.DEFAULT_FROM_EMAIL,
                    [student.parent.email],
                    fail_silently=False
                )
                messages.success(
                    request,
                    f"Email sent to {student.parent.email} for {student.user.full_name} (Course: {class_obj.code})."
                )
            except Exception as e:
                messages.error(request, f"Failed to send email: {e}")
        else:
            messages.warning(request, "Attendance is above 75% or parent email not found.")

        return redirect("attendance_summary", class_id=class_obj.id)

    
    return render(request, "notify_parent.html", {
        "student": student,
        "class_obj": class_obj,
        "percentage": round(percentage, 2),
    })



@login_required
def parent_dashboard(request):
    # ✅ শুধু parent role allowed
    if not hasattr(request.user, 'role') or request.user.role != 'PARENT':
        return redirect('login')

    # ✅ Parent এর সব child বের করো
    children = Student.objects.filter(parent=request.user)

    # ✅ যদি নির্দিষ্ট student select করা হয়
    student_id = request.GET.get('student_id')
    if student_id:
        selected_student = children.filter(id=student_id).first()
        if selected_student:
            children = [selected_student]

    # ✅ Attendance summary বানাও
    summary_data = []
    for student in children:
        assigned_classes = student.classes.all()
        assigned_class_ids = assigned_classes.values_list('id', flat=True)

        records = Attendance.objects.filter(
            student=student,
            class_obj_id__in=assigned_class_ids
        ).select_related('class_obj__time_slot').order_by('-date')

        class_summary = []
        for cls in assigned_classes:
            total = records.filter(class_obj=cls).count()
            present = records.filter(class_obj=cls, status=1).count()
            absent = total - present
            percentage = round((present / total * 100), 2) if total > 0 else 0

            class_summary.append({
                'class_obj': cls,
                'total': total,
                'present': present,
                'absent': absent,
                'percentage': percentage
            })

        summary_data.append({
            'student': student,
            'class_summary': class_summary
        })

    # ✅ Notifications inbox আনো
    notifications = Notification.objects.filter(parent=request.user).order_by('-created_at')

    # ✅ Unread count বের করো
    unread_count = notifications.filter(is_read=False).count()

    # ❌ সব unread notification একসাথে read করে দেওয়া ঠিক না
    # কারণ parent button এ click না করা পর্যন্ত unread থাকা উচিত।
    # তাই এখানে শুধু count পাঠানো হবে, update করা হবে আলাদা view এ।

    return render(request, 'parent_dashboard.html', {
        'summary_data': summary_data,
        'children': children,
        'parent': request.user,
        'notifications': notifications,
        'unread_count': unread_count  # 👈 template এ badge দেখাতে পারবে
    })

@login_required
def parent_notifications(request):
  # ধরে নিচ্ছি Notification model এ parent ফিল্ড আছে যা request.user কে রেফার করে
  notifications = Notification.objects.filter(parent=request.user).order_by('-created_at')
  unread_count = notifications.filter(is_read=False).count()
  return render(request, 'parent_notifications.html', {
      'notifications': notifications,
      'unread_count': unread_count
  })


@login_required
def mark_notification_read(request, note_id):
    note = get_object_or_404(Notification, id=note_id, parent=request.user)
    note.is_read = True
    note.save()
    return redirect('parent_notifications')   # ✅ এখন Notifications পেজে যাবে


@login_required
def notify_parent_view(request, student_id, class_id):
    student = get_object_or_404(Student, id=student_id)
    cls = get_object_or_404(Class, id=class_id)

    # ✅ Attendance percentage হিসাব করো
    records = Attendance.objects.filter(student=student, class_obj=cls)
    total = records.count()
    present = records.filter(status=1).count()
    percentage = round((present / total * 100), 2) if total > 0 else 0

    if request.method == "POST":
        subject = request.POST.get("subject")
        message = request.POST.get("message")
        parent = student.parent

        if parent:
            send_mail(
                subject=subject,
                message=message,
                from_email="noreply@university.com",
                recipient_list=[parent.email],
            )

            Notification.objects.create(
                parent=parent,
                student=student,
                message=message
            )

            return render(request, "notify_parent.html", {
                "student": student,
                "class_obj": cls,
                "percentage": percentage,
                "success": True
            })

    return render(request, "notify_parent.html", {
        "student": student,
        "class_obj": cls,
        "percentage": percentage
    })

@login_required
def download_class_summary_pdf(request, student_id, class_id):
    student = get_object_or_404(Student, id=student_id)
    class_obj = get_object_or_404(Class, id=class_id)

    records = Attendance.objects.filter(student=student, class_obj=class_obj)

    present = records.filter(status=1).count()
    absent = records.filter(status=0).count()
    total = records.count()
    percentage = round((present / total * 100), 2) if total > 0 else 0

    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="{student.user.full_name}_{class_obj.code}.pdf"'

    p = canvas.Canvas(response)
    p.setFont("Helvetica-Bold", 14)
    p.drawString(72, 800, "Class-wise Attendance Summary")
    p.setFont("Helvetica", 12)
    p.drawString(72, 780, f"Student: {student.user.full_name} ({student.roll_no})")
    p.drawString(72, 760, f"Class: {class_obj.code} - {class_obj.title}")
    p.drawString(72, 740, f"Total Classes: {total}")
    p.drawString(72, 720, f"Present: {present}")
    p.drawString(72, 700, f"Absent: {absent}")
    p.drawString(72, 680, f"Attendance Percentage: {percentage}%")

    p.showPage()
    p.save()
    return response



# All summary pdf
@login_required
def download_all_class_summary_pdf(request, student_id):
    student = get_object_or_404(Student, id=student_id)
    # Optional permission check here

    records = Attendance.objects.filter(student=student).select_related('class_obj')
    class_summary = defaultdict(lambda: {
        'class_obj': None, 'present': 0, 'absent': 0, 'total': 0, 'percentage': 0
    })

    for record in records:
        class_obj = record.class_obj
        if not class_obj:
            continue
        cid = class_obj.id
        if class_summary[cid]['class_obj'] is None:
            class_summary[cid]['class_obj'] = class_obj

        if record.status == 1:
            class_summary[cid]['present'] += 1
        else:
            class_summary[cid]['absent'] += 1
        class_summary[cid]['total'] += 1

    for s in class_summary.values():
        if s['total'] > 0:
            s['percentage'] = round(s['present'] / s['total'] * 100, 2)

    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = (
        f'attachment; filename="{student.user.full_name}_class_summaries.pdf"'
    )
    

    p = canvas.Canvas(response)
    p.setFont("Helvetica-Bold", 14)
    p.drawString(72, 800, "Combined Class-wise Attendance Summary")
    p.setFont("Helvetica", 12)
    p.drawString(72, 780, f"Student: {student.user.full_name} ({student.roll_no})")

    y = 750
    for s in class_summary.values():
        if y < 120:  
            p.showPage()
            p.setFont("Helvetica", 12)
            y = 800
        p.setFont("Helvetica-Bold", 12)
        p.drawString(72, y, f"{s['class_obj'].code} - {s['class_obj'].title}")
        y -= 20
        p.setFont("Helvetica", 12)
        p.drawString(92, y, f"Total Classes: {s['total']}")
        y -= 20
        p.drawString(92, y, f"Present: {s['present']}")
        y -= 20
        p.drawString(92, y, f"Absent: {s['absent']}")
        y -= 20
        p.drawString(92, y, f"Attendance Percentage: {s['percentage']}%")
        y -= 30

    p.showPage()
    p.save()
    return response




