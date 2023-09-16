from hvz.models import ClanInvitation, Person, Clan, ClanJoinRequest, NameChangeRequest

def get_notifications(request):
   if request.user.is_authenticated:
      unanswered_invitations = ClanInvitation.objects.filter(invitee=request.user,status='n')
      if Clan.objects.filter(leader=request.user).count() > 0:
         unanswered_requests = ClanJoinRequest.objects.filter(clan=request.user.clan, status='n')
         unanswered_requests_count = unanswered_requests.count()
      else:
         unanswered_requests = []
         unanswered_requests_count = 0
      notification_count = unanswered_invitations.count() + unanswered_requests_count
   else:
      unanswered_invitations = []
      unanswered_requests = []
      notification_count = 0
   name_changes = False
   if request.user.is_authenticated and request.user.admin_this_game:
      if NameChangeRequest.objects.filter(request_status="n").count() > 0:
         notification_count += 1
         name_changes = True
   return {
      'unanswered_invitations':unanswered_invitations, 
      "unanswered_requests": unanswered_requests, 
      "notification_count": notification_count,
      "name_changes_waiting": name_changes
   }