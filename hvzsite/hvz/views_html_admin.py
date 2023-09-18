from django.contrib.sites.shortcuts import get_current_site
from django.db.models import Q, Count
from django.db.models.functions import Lower
from django.http import HttpResponseRedirect
from django.shortcuts import render
from django.utils import timezone

from .decorators import admin_required
from .forms import AboutUpdateForm, AnnouncementForm, AVCreateForm, BlasterApprovalForm, BodyArmorCreateForm, MissionForm, PostGameSurveyForm, ReportUpdateForm, RulesUpdateForm
from .models import get_active_game, reset_active_game
from .models import About, Announcement, AntiVirus, Blaster, BodyArmor, Mission, NameChangeRequest, Person, PlayerStatus, PostGameSurvey, Report, ReportUpdate, Rules, Tag
from .views import for_all_methods


@for_all_methods(admin_required)
class AdminHTMLViews(object):
    def editmissions(request):
        this_game = get_active_game()
        missions = Mission.objects.filter(game=this_game)
        return render(request, "editmissions.html", {'missions':missions.order_by("-go_live_time")})


    def editmission(request, mission_id):    
        if request.method == "GET":
            if mission_id == "new":
                form = MissionForm()
            else:
                form = MissionForm(instance=Mission.objects.get(id=mission_id))
        else:
            if mission_id == "new":
                form = MissionForm(request.POST)
                if form.is_valid():
                    print(form.cleaned_data)
                    mission = form.save()
            else:
                form = MissionForm(request.POST, instance=Mission.objects.get(id=mission_id))
                if form.is_valid():
                    mission = form.save()

            return HttpResponseRedirect("/admin/editmissions/")
        return render(request, "editmission.html", {'form': form, 'mission': mission_id})


    def editpostgamesurvey(request, postgamesurvey_id):
        if request.method == "GET":
            if postgamesurvey_id == "new":
                form = PostGameSurveyForm()
            else:
                form = PostGameSurveyForm(instance=PostGameSurvey.objects.get(id=postgamesurvey_id))
        else:
            if postgamesurvey_id == "new":
                form = PostGameSurveyForm(request.POST)
                if form.is_valid():
                    form.save()
            else:
                form = PostGameSurveyForm(request.POST, instance=PostGameSurvey.objects.get(id=postgamesurvey_id))
                if form.is_valid():
                    form.save()

            return HttpResponseRedirect("/admin/editpostgamesurveys/")
        return render(request, "editpostgamesurvey.html", {'form': form, 'postgamesurvey': postgamesurvey_id})


    def editpostgamesurveys(request):
        this_game = get_active_game()
        surveys = PostGameSurvey.objects.filter(game=this_game)
        return render(request, "editpostgamesurveys.html", {'surveys':surveys.order_by("-go_live_time")})


    def view_unsigned_waivers(request):
        unsigned = PlayerStatus.objects.filter(game=get_active_game(), waiver_signed=False).filter(~Q(status='n'))
        return render(request, "unsigned_waivers.html", {'unsigned':unsigned})
        

    def blasterapproval(request):
        if request.method == "GET":     
            form = BlasterApprovalForm()
            form.fields['owner'].queryset = Person.objects.filter(playerstatus__game=get_active_game()) \
                                                        .filter(playerstatus__status__in=['h','v','e','z','o','x']) \
                                                        .annotate(num_status=Count('playerstatus')) \
                                                        .filter(num_status=1)
        else:
            form = BlasterApprovalForm(request.POST, request.FILES)
            if form.is_valid():
                blaster = Blaster()
                blaster.name = form.cleaned_data['name']
                blaster.owner = form.cleaned_data['owner']
                blaster.game_approved_in = get_active_game()
                blaster.picture = form.cleaned_data['picture']
                blaster.avg_chrono = form.cleaned_data['avg_chrono']
                blaster.save()
                blaster.approved_by.add(request.user)
                blaster.save()
                newform = BlasterApprovalForm()
                return render(request, "blasterapproval.html", {'form':newform, 'approvalcomplete': True})
        return render(request, "blasterapproval.html", {'form':form, 'approvalcomplete': False})


    def admin_create_av(request):    
        if request.method == "GET":     
            form = AVCreateForm()
        else:
            form = AVCreateForm(request.POST)

            if form.is_valid():
                av = form.save()
                newform = AVCreateForm()
                return render(request, "create_av.html", {'form':newform, 'createcomplete': True})
        return render(request, "create_av.html", {'form':form, 'createcomplete': False})


    def admin_view_avs(request):
        game = get_active_game()
        anti_viruses = AntiVirus.objects.filter(game=game)
        context = {"avs": anti_viruses.order_by("-expiration_time")}
        return render(request, "view_avs.html", context)


    def admin_view_tags(request):
        tags = Tag.objects.filter(game=get_active_game()).order_by("-timestamp")
        return render(request, "view_tags.html", {'tags':tags})


    def admin_reset_game(request):
        reset_active_game()
        return HttpResponseRedirect("/")


    def admin_create_body_armor(request):    
        if request.method == "GET":     
            form = BodyArmorCreateForm()
        else:
            form = BodyArmorCreateForm(request.POST)

            if form.is_valid():
                bodyarmor = BodyArmor.objects.create(armor_code=form.cleaned_data['armor_code'], expiration_time=form.cleaned_data['expiration_time'], game = get_active_game())
                bodyarmor.save()
                newform = BodyArmorCreateForm()
                return render(request, "create_body_armor.html", {'form':newform, 'createcomplete': True, 'bodyarmor': bodyarmor})
        return render(request, "create_body_armor.html", {'form':form, 'createcomplete': False})


    def player_activation(request):
        context = {}
        return render(request, "player_activation.html", context)


    def player_oz_activation(request):
        context = {}
        return render(request, "player_oz_activation.html", context)


    def bodyarmors(request):
        game = get_active_game()
        body_armors = BodyArmor.objects.filter(game=game)
        context = {"bodyarmors": body_armors.order_by("-expiration_time")}
        return render(request, "bodyarmors.html", context)


    def bodyarmor_view(request, armor_id):
        armor = BodyArmor.objects.get(armor_uuid=armor_id)
        context = {
            'armor': armor,
        }
        return render(request, "bodyarmor.html", context)


    def av_view(request, av_id):
        av = AntiVirus.objects.get(av_uuid=av_id)
        context = {
            'av': av,
        }
        return render(request, "av_view.html", context)


    def reports(request):
        game = get_active_game()
        reports = Report.objects.filter(game=game)
        context = {"reports": reports.order_by("-timestamp")}
        return render(request, "reports.html", context)


    def report(request, report_id):
        report = Report.objects.get(report_uuid=report_id)
        if request.method == "POST":
            form = ReportUpdateForm(request.POST, report=report)
            if form.is_valid():
                form_reportees = set(form.cleaned_data['reportees'])
                new_update = form.instance
                new_update.note_creator = request.user
                new_update.report = Report.objects.get(report_uuid=report_id)
                existing_reportees = set(new_update.report.reportees.get_queryset())
                new_reportees = form_reportees - existing_reportees
                deleted_reportees = existing_reportees - form_reportees
                print(new_reportees)
                print(deleted_reportees)
                print(existing_reportees.intersection(form_reportees))
                new_update.report.reportees.set(form_reportees)
                new_update.report.save()
                if len(new_reportees) > 0 or len(deleted_reportees) > 0:
                    new_note = ""
                    if len(new_reportees) > 0:
                        new_note += f"-{request.user} added {', '.join([str(reportee) for reportee in new_reportees])} as Reportees-\n"
                    if len(deleted_reportees) > 0:
                        new_note += f"-{request.user} removed {', '.join([str(reportee) for reportee in deleted_reportees])} as Reportees-"
                    reportee_change_update = ReportUpdate.objects.create(note=new_note, note_creator=request.user, report=new_update.report)
                    reportee_change_update.save()
                if form.cleaned_data['update_status'] != 'x':
                    new_update.report.status = form.cleaned_data['update_status']
                    new_update.report.save()
                    status_change_update = ReportUpdate.objects.create(note=f"-{request.user} changed the status of this report to {new_update.report.status_text}-", note_creator=request.user, report=new_update.report)
                    status_change_update.save()
                new_update.save()
                form = ReportUpdateForm(report=report)
        else:
            form = ReportUpdateForm(report=report)
        report = Report.objects.get(report_uuid=report_id)
        context = {
            'report': report,
            'form': form
        }
        return render(request, "report.html", context)


    def rules_update(request):
        if request.method == "POST":
            form = RulesUpdateForm(request.POST)
            if form.is_valid():
                rules_obj = form.instance
                rules_obj.last_edited_by = request.user
                rules_obj.last_edited_datetime = timezone.localtime()
                rules_obj.save()
                return HttpResponseRedirect("/rules/")
        else:
            form = RulesUpdateForm(instance= Rules.load())
        rules = Rules.load()
        context = {
            'rules': rules,
            'form': form
        }
        return render(request, "rules_update.html", context)


    def about_update(request):
        if request.method == "POST":
            form = AboutUpdateForm(request.POST)
            if form.is_valid():
                about_obj = form.instance
                about_obj.last_edited_by = request.user
                about_obj.last_edited_datetime = timezone.localtime()
                about_obj.save()
                return HttpResponseRedirect("/about/")
        else:
            form = AboutUpdateForm(instance=About.load())
        about = About.load()
        context = {
            'about': about,
            'form': form
        }
        return render(request, "about_update.html", context)


    def print_one(request, player_uuid):
        context = {
            "players": Person.objects.filter(player_uuid=player_uuid),
            "preview": False,
            "print_one": True,
            "url": f"{request.scheme}://{get_current_site(request)}"
        }
        return render(request, "print_cards.html", context)


    def print_ids(request, preview=False):
        to_print = PlayerStatus.objects.filter(printed=False, game=get_active_game()).filter(~Q(status='n')).order_by(Lower('player__first_name'), Lower('player__last_name'))
        context = {
            "players": [status.player for status in to_print],
            "preview": preview,
            "print_one": False,
            "url": f"{request.scheme}://{get_current_site(request)}"
        }
        return render(request, "print_cards.html", context)


    def print_preview(request):
        return AdminHTMLViews.print_ids(request, True)


    def mark_printed(request):
        PlayerStatus.objects.filter(printed=False, game=get_active_game()).filter(~Q(status='n')).update(printed=True)
        return HttpResponseRedirect("/")


    def view_failed_av_list(request):
        offenders = Person.objects.annotate(failcount=Count("failed_av_attempts")).filter(failcount__gt=0).order_by("-failcount")
        context = {
            "offenders": offenders
        }
        return render(request, "failed_av_list.html", context)
    
    
    def manage_announcements(request):
        announcements = Announcement.objects.all().order_by('-post_time')
        return render(request, "manage_announcements.html", {'announcements':announcements})


    def edit_announcement(request, announcement_id):
        if request.method == "GET":
            if announcement_id == "new":
                form = AnnouncementForm()
            else:
                form = AnnouncementForm(instance=Announcement.objects.get(id=announcement_id))
        else:
            if announcement_id == "new":
                form = AnnouncementForm(request.POST)
            else:
                form = AnnouncementForm(request.POST, instance=Announcement.objects.get(id=announcement_id))

            if form.is_valid():
                announcement = form.save()
                return HttpResponseRedirect(f"/announcement/{announcement.id}/")
        return render(request, "edit_announcement.html", {'form':form})


    def view_announcement(request, announcement_id):
        try:
            announcement = Announcement.objects.get(id=announcement_id)
            return render(request, "announcement.html", {'announcement':announcement})
        except:
            return HttpResponseRedirect("/")
            
    def view_name_change_requests(request):
        current_requests = NameChangeRequest.objects.filter(request_status='n').order_by("request_open_timestamp")
        previous_requests = NameChangeRequest.objects.filter(request_status__in=['c','r','a']).order_by("request_open_timestamp")
        return render(request, "name_change_list.html", {'current_requests': current_requests, 'previous_requests': previous_requests})

