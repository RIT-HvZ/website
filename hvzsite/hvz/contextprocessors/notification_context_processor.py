from hvz.models import ClanInvitation, Person, Clan, ClanJoinRequest

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
   return {'unanswered_invitations':unanswered_invitations, "unanswered_requests": unanswered_requests, "notification_count": notification_count} #or whatever you want to set to variable ss