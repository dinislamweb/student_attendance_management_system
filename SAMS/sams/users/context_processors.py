from .models import Notification

def unread_notifications(request):
    # Anonymous user হলে কিছু দেখাবে না
    if not request.user.is_authenticated:
        return {}

    # শুধু parent role হলে notification count দেখাও
    if hasattr(request.user, 'role') and request.user.role == 'PARENT':
        unread_count = Notification.objects.filter(parent=request.user, is_read=False).count()
        return {'navbar_unread_count': unread_count}
    
    return {}