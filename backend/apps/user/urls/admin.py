from django.urls import path
from apps.user.views.admin import (
    AdminUserDetailView,
    AdminUserListView,
    AdminUserTriggerPasswordResetView,
    AdminUserTriggerVerificationView,
)

urlpatterns = [
    path('users/', AdminUserListView.as_view(), name='admin-users-list'),
    path('users/<uuid:id>/', AdminUserDetailView.as_view(), name='admin-user-detail'),
    path(
        'users/<uuid:id>/trigger-password-reset/',
        AdminUserTriggerPasswordResetView.as_view(),
        name='admin-user-trigger-password-reset',
    ),
    path(
        'users/<uuid:id>/trigger-verification/',
        AdminUserTriggerVerificationView.as_view(),
        name='admin-user-trigger-verification',
    ),
]
