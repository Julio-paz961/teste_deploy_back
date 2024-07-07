from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import MessageViewSet, read_posts, read_post

router = DefaultRouter()
router.register(r'posts', MessageViewSet)

urlpatterns = [
    path('', include(router.urls)),
    path('posts/', read_posts),
    path('posts/<str:post_id>/', read_post),
]
