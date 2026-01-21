import functools

from django.http import JsonResponse
from django.shortcuts import redirect


def authentication_required(view_func):
    @functools.wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if request.user.is_authenticated:
            return view_func(request,*args, **kwargs)
        return redirect(f"/accounts/login/?next={request.get_full_path()}")
    return wrapper


def authentication_required_api(view_func):
    @functools.wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if request.user.is_authenticated:
            return view_func(request,*args, **kwargs)
        response = JsonResponse({"status": "only authenticated players can use this API"})
        response.status_code = 403
        return response
    return wrapper


def admin_required(view_func):
    @functools.wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if request.user.is_authenticated and request.user.admin_this_game:
            return view_func(request,*args, **kwargs)
        return redirect(f"/accounts/login/?next={request.get_full_path()}")
    return wrapper


def admin_required_api(view_func):
    @functools.wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if request.user.is_authenticated and request.user.admin_this_game:
            return view_func(request,*args, **kwargs)
        response = JsonResponse({"status": "only admins can use this API"})
        response.status_code = 403
        return response
    return wrapper


def active_player_required(view_func):
    @functools.wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if request.user.is_authenticated and request.user.active_this_game:
            return view_func(request,*args, **kwargs)
        return redirect(f"/accounts/login/?next={request.get_full_path()}")
    return wrapper


def staff_required(view_func):
    @functools.wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if request.user.is_authenticated and request.user.admin_this_game or request.user.mod_this_game:
            return view_func(request,*args, **kwargs)
        return redirect(f"/accounts/login/?next={request.get_full_path()}")
    return wrapper


def staff_required_api(view_func):
    @functools.wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if request.user.is_authenticated and request.user.admin_this_game or request.user.mod_this_game:
            return view_func(request,*args, **kwargs)
        response = JsonResponse({"status": "only staff can use this API"})
        response.status_code = 403
        return response
    return wrapper