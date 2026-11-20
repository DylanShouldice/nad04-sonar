from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import JsonResponse
from django.shortcuts import render
from django.views import View

from .forms import ProfileForm
from .models import Profile


class MyProfileView(LoginRequiredMixin, View):
    """Render the current user's profile on GET and update it on AJAX POST."""

    def get(self, request):
        obj = Profile.objects.get(user=request.user)
        form = ProfileForm(instance=obj)
        return render(request, 'profiles/main.html', {'obj': obj, 'form': form})

    def post(self, request):
        obj = Profile.objects.get(user=request.user)
        form = ProfileForm(request.POST, request.FILES, instance=obj)
        if request.headers.get('x-requested-with') == 'XMLHttpRequest' and form.is_valid():
            instance = form.save()
            return JsonResponse({
                'bio': instance.bio,
                'avatar': instance.avatar.url,
                'user': instance.user.username,
            })
        return render(request, 'profiles/main.html', {'obj': obj, 'form': form})


my_profile_view = MyProfileView.as_view()