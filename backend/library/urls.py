from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import BookViewSet, InventoryOperationViewSet, LoanViewSet, MemberViewSet, VirtualRequestViewSet, login, me, signup

router = DefaultRouter()
router.register("books", BookViewSet)
router.register("loans", LoanViewSet, basename="loan")
router.register("virtual-requests", VirtualRequestViewSet, basename="virtual-request")
router.register("inventory", InventoryOperationViewSet, basename="inventory")
router.register("members", MemberViewSet)

urlpatterns = [
    path("auth/signup/", signup),
    path("auth/login/", login),
    path("auth/me/", me),
    path("", include(router.urls)),
]