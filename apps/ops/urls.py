# coding=utf-8

from django.urls import path
from . import views

# from django.urls import reverse_lazy

urlpatterns = [

    path('user/add/', views.UserAdd.as_view(), name="userprofile_add"),
    path('user/delete/', views.UserDelete.as_view(), name="userprofile_delete"),
    path('user/<int:pk>/update/', views.UserUpdate.as_view(), name="userprofile_update"),
    path('user/', views.UserList.as_view(), name="userprofile_list"),

    path('group/add/', views.GroupAdd.as_view(), name="group_add"),
    path('group/delete/', views.GroupDelete.as_view(), name="group_delete"),
    path('group/<int:pk>/update/', views.GroupUpdate.as_view(), name="group_update"),
    path('group/', views.GroupList.as_view(), name="group_list"),

]

