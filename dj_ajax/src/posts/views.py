from pydoc import visiblename
from django.shortcuts import redirect, render
from .models import Post, Photo
from django.http import JsonResponse, HttpResponse
from .forms import PostForm
from profiles.models import Profile
from .utils import action_permission
from django.contrib.auth.decorators import login_required
from django.db.models import Q

@login_required
def post_list_and_create(request):
    form = PostForm(request.POST or None)

    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        if form.is_valid():
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
    context = {
        'form': form,
    }
    return render(request, 'posts/main.html', context)

@login_required
def post_detail(request, pk):
    obj = Post.objects.get(pk=pk)
    form = PostForm()

    context = {
        'obj': obj,
        'form': form,
    }
    return render(request, 'posts/detail.html', context)

@login_required
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

@action_permission
@login_required
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


@action_permission
@login_required
def delete_post(request, pk):
    obj = Post.objects.get(pk=pk)
    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        obj.delete()
        return JsonResponse({'msg': 'Post Deleted'})
    return redirect('posts:main-board')

@login_required
def image_upload_view(request):
    if request.method == 'POST':
        img = request.FILES.get('file')
        post_id = request.POST.get('post_id')
        post = Post.objects.get(id=post_id)
        Photo.objects.create(image=img, post=post)
        return JsonResponse({'message': 'Image uploaded successfully!'})
    return JsonResponse({'error': 'Invalid request'}, status=400)

@login_required
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
