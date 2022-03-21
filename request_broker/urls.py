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
from django.contrib import admin
from django.urls import path

from process_request.views import (DeliverDuplicationRequestView,
                                   DeliverReadingRoomRequestView,
                                   DownloadCSVView, LinkResolverView,
                                   MailerView, ParseRequestView, PingView)

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/deliver-request/email", MailerView.as_view(), name="deliver-email"),
    path("api/deliver-request/duplication", DeliverDuplicationRequestView.as_view(), name="deliver-duplication"),
    path("api/deliver-request/reading-room", DeliverReadingRoomRequestView.as_view(), name="deliver-readingroom"),
    path("api/process-request/parse", ParseRequestView.as_view(), name="parse-request"),
    path("api/process-request/resolve", LinkResolverView.as_view(), name="resolve-request"),
    path("api/download-csv/", DownloadCSVView.as_view(), name="download-csv"),
    path("api/status/", PingView.as_view(), name="ping")
]
