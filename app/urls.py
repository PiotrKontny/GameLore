from django.urls import path, include
from . import views

urlpatterns = [
    # --- Strony główne ---
    #path('', views.home, name="home"),
    path("explore/", views.explore_view, name="explore"),
    path("my_library/", views.my_library_view, name="my_library"),
    path("api/my_library/", views.my_library_api, name="my_library_api"),
    path("delete_history/", views.delete_history_entry, name="delete_history"),
    path("information/", views.information_view, name="information"),

    path("profile/", views.react_index, name="profile_page"),
    path("api/profile/", views.profile_view, name="api_profile"),

    # --- Logowanie / Rejestracja ---
    path('register/', views.RegisterUser.as_view(), name='register'),
    path('login/', views.LoginView.as_view(), name='login'),
    path("api/user/", views.api_user, name="api_user"),

    # --- Wyszukiwanie i gry ---
    path('search/', views.search_view, name='search'),
    path('results/', views.results_view, name='results'),
    path('details/', views.details_view, name='details'),
    path('games/<int:pk>/', views.game_detail_page, name='game_detail_page'),
    path("api/game/<int:pk>/", views.game_detail_api, name="game_detail_api"),
    path("app/api/game/<int:pk>/", views.game_detail_api),
    path('games/<int:pk>/rating/', views.game_rating_view, name="game_rating"),
    path('compilation/', views.compilation_view, name='compilation'),
    path("games/<int:pk>/generate-summary/", views.generate_summary_view, name="generate_summary"),

    # --- Admin panel główny ---
    path("admin-panel/", views.admin_panel, name="admin_panel"),

    # --- Nowe podstrony admina ---
    path("admin-panel/users/", views.admin_users_view, name="admin_users"),
    path("admin-panel/games/", views.admin_games_view, name="admin_games"),

    # --- Akcje admina (AJAX) ---
    path("admin-panel/delete-user/<int:user_id>/", views.admin_delete_user, name="admin_delete_user"),
    path("admin-panel/delete-game/<int:game_id>/", views.admin_delete_game, name="admin_delete_game"),
    path("admin-panel/edit-game-score/<int:game_id>/", views.admin_edit_game_score, name="admin_edit_game_score"),
    path("admin-panel/reload-game/<int:game_id>/", views.admin_reload_game, name="admin_reload_game"),

    # --- Chatbot i historia ---
    path("chatbot/", views.chatbot_page, name="chatbot_page"),
    path("chatbot/ask/", views.chatbot_ask, name="chatbot_ask"),
    path("chatbot/history/", views.chatbot_history, name="chatbot_history"),
    path("delete_history/", views.delete_history_entry, name="delete_history_entry"),
    path("chatbot/delete/", views.delete_chat_history, name="delete_chat_history"),
]
