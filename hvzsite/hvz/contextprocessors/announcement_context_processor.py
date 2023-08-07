from hvz.models import Announcement

def get_announcements(request):
   announcements = Announcement.objects.filter(active=True).order_by('-post_time')
   return {'announcements': announcements}