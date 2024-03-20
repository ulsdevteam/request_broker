"""request_broker URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/2.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.urls import path

from process_request.views import (AeonReadingRoomsView,
                                   DeliverDuplicationRequestView,
                                   DeliverReadingRoomRequestView,
                                   DownloadCSVView, LinkResolverView,
                                   MailerView, ParseBatchRequestView,
                                   ParseItemRequestView, PingView)

urlpatterns = [
    path("api/deliver-request/email", MailerView.as_view(), name="deliver-email"),
    path("api/deliver-request/duplication", DeliverDuplicationRequestView.as_view(), name="deliver-duplication"),
    path("api/deliver-request/reading-room", DeliverReadingRoomRequestView.as_view(), name="deliver-readingroom"),
    path("api/process-request/parse", ParseItemRequestView.as_view(), name="parse-individual"),
    path("api/process-request/parse-batch", ParseBatchRequestView.as_view(), name="parse-batch"),
    path("api/process-request/resolve", LinkResolverView.as_view(), name="resolve-request"),
    path("api/download-csv/", DownloadCSVView.as_view(), name="download-csv"),
    path("api/reading-rooms/", AeonReadingRoomsView.as_view(), name="get-readingrooms"),
    path("api/status/", PingView.as_view(), name="ping")
]
