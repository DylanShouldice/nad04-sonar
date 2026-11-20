# Here is where the URLS for our web app ar defined, we import all the functions that are exposed to users
# that they need to complete their task of posting a blog, much like creating a handler for a URL in Go, but go seems to wrap it more into the 1 function


from django.urls import path
from .views import (
    delete_post,
    load_post_data_view,
    post_list_and_create,
    like_unlike_post,
    post_detail,
    post_detail_data_view,
    delete_post,
    update_post,
    image_upload_view,
    like_unlike_post_via_url,
    search_posts,
)

app_name = 'posts'

urlpatterns = [
    path('', post_list_and_create, name='main-board'),
    path('search/', search_posts, name='search-posts'), # Talk about the error where the order of url patterns matter
    path('like-unlike/', like_unlike_post, name='like-unlike'),
    path('<int:pk>/like-unlike/', like_unlike_post_via_url, name='like-unlike-via-url'),
    path('upload/', image_upload_view, name='image-upload'),
    path('data/<int:num_posts>/', load_post_data_view, name='posts-data'),
    path('<pk>/', post_detail, name='post-detail'),
    path('<pk>/update/', update_post, name='post-update'),
    path('<pk>/delete/', delete_post, name='post-delete'),
    path('<pk>/data/', post_detail_data_view, name='post-detail-data'),
]