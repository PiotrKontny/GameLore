from django.shortcuts import render
from django.http import HttpResponse
from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenObtainPairView
from django.contrib.auth import get_user_model, user_logged_in
from .serializers import (GamesSerializer, GamePlotsSerializer, UserHistorySerializer, UserSerializer,
                          ChatBotSerializer)
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from .models import Games, GamePlots, UserModel, UserHistory, ChatBot
from rest_framework.permissions import AllowAny, IsAuthenticated
from django.core.cache import cache

# Create your views here.
def main(request):
    return HttpResponse("Hello")

class UserView(generics.ListCreateAPIView):
    queryset = UserModel.objects.all()  # Zapytanie do SQL o wszystkich użytkowników
    serializer_class = UserSerializer  # Serializer do danych użytkownika
    permission_classes = [AllowAny]

class LoginOrEmailTokenObtainPairSerializer(TokenObtainPairSerializer):
    def validate(self, attrs):
        User = get_user_model()
        uname_field = User.USERNAME_FIELD  # "username" albo "email"
        if uname_field not in attrs:
            login_val = (
                self.initial_data.get("login")
                or self.initial_data.get("username")
                or self.initial_data.get("email")
            )
            if login_val:
                attrs[uname_field] = login_val
        return super().validate(attrs)

class LoginView(TokenObtainPairView):
    serializer_class = LoginOrEmailTokenObtainPairSerializer

class RegisterUser(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        users = UserModel.objects.all()
        serializer = UserSerializer(users, many=True)
        return Response(serializer.data)
    def post(self,request):
        print(request.data)
        serializer = UserSerializer(data=request.data)

        if serializer.is_valid():
            user = serializer.save()
            return Response({"message": "User created successfully!", "user_id": user.id}, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)



class GamePlotsView(generics.CreateAPIView):
    queryset = GamePlots.objects.all()
    serializer_class = GamePlotsSerializer

