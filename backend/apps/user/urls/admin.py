from django.urls import path
from apps.user.views.admin import AdminUserListView

urlpatterns = [
    path('users/', AdminUserListView.as_view(), name='admin-users-list'),
]
