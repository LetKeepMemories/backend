from django.http import HttpResponse
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAdminUser
from rest_framework.response import Response

from apps.user.models import User
from apps.event.models import Occasion
from apps.subscription.models import UserSubscription

def landing_page(request):
    html = """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Lets Keep Memories API</title>
        <style>
            body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif; display: flex; justify-content: center; align-items: center; height: 100vh; margin: 0; background-color: #f9fafb; color: #111827; }
            .container { text-align: center; background: white; padding: 2rem 3rem; border-radius: 8px; box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1); }
            h1 { margin-top: 0; color: #2563eb; }
            p { color: #4b5563; }
            a { color: #2563eb; text-decoration: none; font-weight: bold; }
            a:hover { text-decoration: underline; }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>Lets Keep Memories API</h1>
            <p>The API is up and running securely.</p>
            <p><a href="/api/docs/">View Swagger Documentation</a></p>
        </div>
    </body>
    </html>
    """
    return HttpResponse(html)

@api_view(["GET"])
@permission_classes([IsAdminUser])
def admin_stats(request):
    total_users = User.objects.count()
    total_occasions = Occasion.objects.count()
    active_subscriptions = UserSubscription.objects.filter(status=UserSubscription.Status.ACTIVE).count()
    
    return Response({
        "total_users": total_users,
        "total_occasions": total_occasions,
        "active_subscriptions": active_subscriptions
    })
