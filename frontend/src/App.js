import React, { useEffect } from "react";
import {
  BrowserRouter,
  Routes,
  Route,
  useNavigate,
} from "react-router-dom";

import { setNavigate } from "./utils/navigateGlobal";

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

import AdminHomePage from "./pages/AdminHome";
import AdminPanelPage from "./pages/AdminPanelPage";
import AdminUsersPage from "./pages/AdminUsersPage";
import AdminGamesPage from "./pages/AdminGamesPage";

import ErrorPage from "./pages/ErrorPage";

function NavigationHandler() {
  const navigate = useNavigate();
  useEffect(() => setNavigate(navigate), [navigate]);
  return null;
}

function App() {
  return (
    <BrowserRouter>
      <NavigationHandler />

      <Routes>
        <Route
          path="/error/401"
          element={
            <>
              <NavbarLogin />
              <ErrorPage code={401} message="Unauthorized – please log in." />
            </>
          }
        />

        <Route
          path="/error/403"
          element={
            <>
              <Navbar />
              <ErrorPage code={403} message="Access denied – insufficient permissions." />
            </>
          }
        />

        <Route
          path="/error/404"
          element={
            <>
              <Navbar />
              <ErrorPage code={404} message="Page not found." />
            </>
          }
        />

        <Route
          path="/error/500"
          element={
            <>
              <Navbar />
              <ErrorPage code={500} message="Internal server error. Please try again later." />
            </>
          }
        />

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

        <Route path="/" element={<HomePage />} />
        <Route path="/app/information/" element={<InformationPage />} />

        <Route path="/app/admin-panel/" element={<AdminPanelPage />} />
        <Route path="/app/admin-panel/users/" element={<AdminUsersPage />} />
        <Route path="/app/admin-panel/games/" element={<AdminGamesPage />} />

        <Route
          path="/app/*"
          element={
            <Routes>
              <Route path="explore/" element={<ExplorePage />} />
              <Route
                path="profile/"
                element={
                  <>
                    <Navbar />
                    <ProfilePage />
                  </>
                }
              />

              <Route
                path="my_library/"
                element={
                  <>
                    <Navbar />
                    <MyLibraryPage />
                  </>
                }
              />

              <Route
                path="chatbot/"
                element={
                  <>
                    <Navbar />
                    <ChatbotPage />
                  </>
                }
              />

              <Route
                path="search/"
                element={
                  <>
                    <Navbar />
                    <SearchFormPage />
                  </>
                }
              />

              <Route
                path="results/"
                element={
                  <>
                    <Navbar />
                    <SearchResultsPage />
                  </>
                }
              />

              <Route
                path="compilation/"
                element={
                  <>
                    <Navbar />
                    <CompilationPage />
                  </>
                }
              />

              <Route
                path="details/"
                element={
                  <>
                    <Navbar />
                    <DetailsRedirectPage />
                  </>
                }
              />

              <Route
                path="games/:id"
                element={
                  <>
                    <Navbar />
                    <GameDetailPage />
                  </>
                }
              />

              <Route
                path="admin/home/"
                element={
                  <>
                    <Navbar />
                    <AdminHomePage />
                  </>
                }
              />

              <Route
                path="*"
                element={<ErrorPage code={404} message="Page not found" />}
              />
            </Routes>
          }
        />

        <Route
          path="*"
          element={
            <>
              <Navbar />
              <ErrorPage code={404} message="Page not found" />
            </>
          }
        />
      </Routes>
    </BrowserRouter>
  );
}

export default App;
