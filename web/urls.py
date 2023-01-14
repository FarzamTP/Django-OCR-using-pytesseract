from django.urls import path
from . import views
from django.conf.urls.static import static
from django.conf import settings

urlpatterns = [
    path('', views.index, name='index'),
    path('receipt/<int:receipt_pk>/<int:confidence_rate>', views.render_receipt, name='render_receipt'),
    path('receipt/<int:receipt_pk>/submit_receipt/', views.process_submitted_data, name='process_submitted_data'),
    path('authenticate_private_key/', views.check_user_private_key, name='check_user_private_key'),
]

urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
