from rest_framework import viewsets

class BaseViewSet(viewsets.ModelViewSet):
    """
    A base viewset that defaults to ordering by latest creation.
    Can be inherited by other viewsets across the project.
    """
    ordering = ["-created_at"]
    
    def get_queryset(self):
        qs = super().get_queryset()
        if hasattr(qs.model, 'created_at') and not qs.query.order_by:
            qs = qs.order_by("-created_at")
        return qs
