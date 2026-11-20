from django.shortcuts import redirect
from .models import Post
from profiles.models import Profile
from django.http import HttpResponse
from django.http import JsonResponse

def action_permission(func):
    def wrapper(request, **kwargs):
        pk = kwargs.get('pk')
        try:
            profile = Profile.objects.get(user=request.user)
            post = Post.objects.get(pk=pk)
            if profile == post.author:  # Ensure comparison is between Profile objects
                return func(request, **kwargs)
            else:
                return redirect('posts:main-board')
        except Profile.DoesNotExist:
            return JsonResponse({'error': 'Profile not found.'}, status=404)
        except Post.DoesNotExist:
            return JsonResponse({'error': 'Post not found.'}, status=404)
    return wrapper