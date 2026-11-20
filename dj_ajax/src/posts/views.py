from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Q
from django.http import JsonResponse
from django.shortcuts import redirect, render
from django.views import View
from django.views.decorators.http import require_GET, require_POST

from profiles.models import Profile
from .forms import PostForm
from .models import Photo, Post
from .utils import action_permission


class PostListAndCreateView(LoginRequiredMixin, View):
    """Render the main post board on GET and create a post on AJAX POST."""

    def get(self, request):
        form = PostForm()
        return render(request, 'posts/main.html', {'form': form})

    def post(self, request):
        form = PostForm(request.POST)
        if request.headers.get('x-requested-with') == 'XMLHttpRequest' and form.is_valid():
            author = Profile.objects.get(user=request.user)
            instance = form.save(commit=False)
            instance.author = author
            instance.save()
            return JsonResponse({
                'title': instance.title,
                'body': instance.body,
                'author': instance.author.user.username,
                'id': instance.id,
            })
        return render(request, 'posts/main.html', {'form': form})


post_list_and_create = PostListAndCreateView.as_view()


@login_required
@require_GET
def post_detail(request, pk):
    obj = Post.objects.get(pk=pk)
    form = PostForm()

    context = {
        'obj': obj,
        'form': form,
    }
    return render(request, 'posts/detail.html', context)


@login_required
@require_GET
def load_post_data_view(request, num_posts):
    if request.headers.get('x-requested-with') == 'XMLHttpRequest':

        visible = 3
        upper = num_posts
        lower = upper - visible
        size = Post.objects.all().count()

        qs = Post.objects.all()
        data = []
        for obj in qs:
            item = {
                'id': obj.id,
                'title': obj.title,
                'body': obj.body,
                'liked': True if request.user in obj.liked.all() else False,
                'count': obj.like_count,
                'author': obj.author.user.username
            }

            data.append(item)
        return JsonResponse({'data': data[lower:upper], 'size': size})


@login_required
@require_GET
def post_detail_data_view(request, pk):
    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        obj = Post.objects.get(pk=pk)
        data = {
            'id': obj.id,
            'title': obj.title,
            'body': obj.body,
            'author': obj.author.user.username,
            'author_avatar': obj.author.avatar.url if obj.author.avatar else None,
            'logged_in': request.user.username,
            'liked': True if request.user in obj.liked.all() else False,
            'count': obj.like_count,

        }
        return JsonResponse({'data': data})
    return redirect('posts:main-board')


@login_required
@require_POST
def like_unlike_post(request):
    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        pk = request.POST.get('pk')
        obj = Post.objects.get(pk=pk)
        if request.user in obj.liked.all():
            liked = False
            obj.liked.remove(request.user)
        else:
            liked = True
            obj.liked.add(request.user)
        return JsonResponse({'liked': liked, 'count': obj.like_count})
    return redirect('posts:main-board')


@login_required
@require_POST
def like_unlike_post_via_url(request, pk):
    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        obj = Post.objects.get(pk=pk)
        if request.user in obj.liked.all():
            liked = False
            obj.liked.remove(request.user)
        else:
            liked = True
            obj.liked.add(request.user)
        return JsonResponse({'liked': liked, 'count': obj.liked.count()})
    return JsonResponse({'error': 'Invalid request'}, status=400)

@login_required
@require_POST
@action_permission
def update_post(request, pk):
    obj = Post.objects.get(pk=pk)
    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        new_title = request.POST.get('title')
        new_body = request.POST.get('body')
        obj.title = new_title
        obj.body = new_body
        obj.save()
        return JsonResponse({
            'title': new_title,
            'body': new_body,
        })
    return redirect('posts:main-board')


@login_required
@require_POST
@action_permission
def delete_post(request, pk):
    obj = Post.objects.get(pk=pk)
    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        obj.delete()
        return JsonResponse({'msg': 'Post Deleted'})
    return redirect('posts:main-board')


@login_required
@require_POST
def image_upload_view(request):
    img = request.FILES.get('file')
    post_id = request.POST.get('post_id') or request.POST.get('new_post_id')
    if not img or not post_id:
        return JsonResponse({'error': 'Invalid upload request.'}, status=400)

    try:
        post = Post.objects.get(id=post_id)
    except (Post.DoesNotExist, ValueError, TypeError):
        return JsonResponse({'error': 'Post not found.'}, status=404)

    profile = Profile.objects.get(user=request.user)
    if post.author != profile:
        return JsonResponse({'error': 'Forbidden'}, status=403)

    Photo.objects.create(image=img, post=post)
    return JsonResponse({'message': 'Image uploaded successfully!'})

@login_required
@require_GET
def search_posts(request):
    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        query = request.GET.get('q', '').strip()
        if not query:
            return JsonResponse({'data': []})

        try:
            # Filter posts by title or body
            posts = Post.objects.filter(
                Q(title__icontains=query) | Q(body__icontains=query)
            ).distinct()

            # Serialize the data
            data = [
                {
                    'id': post.id,
                    'title': post.title,
                    'body': post.body,
                    'liked': True if request.user in post.liked.all() else False,
                    'count': post.like_count,
                }
                for post in posts
            ]
            return JsonResponse({'data': data})
        except Exception as e:
            print(f"Error during search: {e}")  # Log the error
            return JsonResponse({'error': 'Something went wrong during the search.'}, status=500)

    return JsonResponse({'error': 'Invalid request'}, status=400)
