import React from "react";
import { BrowserRouter, Routes, Route } from "react-router-dom";

import Navbar from "./components/Navbar";
import NavbarLogin from "./components/NavbarLogin";

import HomePage from "./pages/HomePage";
import LoginPage from "./pages/LoginPage";
import RegisterPage from "./pages/RegisterPage";
import InformationPage from "./pages/InformationPage";
import ExplorePage from "./pages/ExplorePage";
import SearchFormPage from "./pages/SearchFormPage";
import SearchResultsPage from "./pages/SearchResultsPage";
import DetailsRedirectPage from "./pages/DetailsRedirectPage";
import GameDetailPage from "./pages/GameDetailPage";
import ProfilePage from "./pages/ProfilePage";
import MyLibraryPage from "./pages/MyLibraryPage";
import ChatbotPage from "./pages/ChatbotPage";
import CompilationPage from "./pages/CompilationPage";

// ADMIN
import AdminHomePage from "./pages/AdminHome";
import AdminPanelPage from "./pages/AdminPanelPage";
import AdminUsersPage from "./pages/AdminUsersPage";
import AdminGamesPage from "./pages/AdminGamesPage";

// ERROR
import ErrorPage from "./pages/ErrorPage";

function App() {
  return (
    <BrowserRouter>
      <Routes>
        {/* LOGIN / REGISTER */}
        <Route
          path="/app/login/"
          element={
            <>
              <NavbarLogin />
              <LoginPage />
            </>
          }
        />

        <Route
          path="/app/register/"
          element={
            <>
              <NavbarLogin />
              <RegisterPage />
            </>
          }
        />

        {/* HOME */}
        <Route path="/" element={<HomePage />} />

        {/* INFORMATION */}
        <Route path="/app/information/" element={<InformationPage />} />

        {/* === ADMIN PANEL – BEZ STANDARDOWEGO NAVBARA === */}
        <Route path="/app/admin-panel/" element={<AdminPanelPage />} />
        <Route path="/app/admin-panel/users/" element={<AdminUsersPage />} />
        <Route path="/app/admin-panel/games/" element={<AdminGamesPage />} />

        {/* === POZOSTAŁE STRONY Z NORMALNYM NAVBAREM === */}
        <Route
          path="/app/*"
          element={
            <>
              <Navbar />
              <Routes>
                <Route path="profile/" element={<ProfilePage />} />
                <Route path="my_library/" element={<MyLibraryPage />} />
                <Route path="chatbot/" element={<ChatbotPage />} />
                <Route path="explore/" element={<ExplorePage />} />
                <Route path="search/" element={<SearchFormPage />} />
                <Route path="results/" element={<SearchResultsPage />} />
                <Route path="compilation/" element={<CompilationPage />} />
                <Route path="details/" element={<DetailsRedirectPage />} />
                <Route path="games/:id" element={<GameDetailPage />} />

                {/* Admin HOME używa zwykłego Navbara */}
                <Route path="admin/home/" element={<AdminHomePage />} />

                <Route
                  path="*"
                  element={<ErrorPage code={404} message="Page not found" />}
                />
              </Routes>
            </>
          }
        />
      </Routes>
    </BrowserRouter>
  );
}

export default App;
