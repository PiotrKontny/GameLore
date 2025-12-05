import React from "react";
import { Link } from "react-router-dom";
import "./NavbarLogin.css";

function NavbarLogin() {
  return (
    <nav className="navbar-login">
      <div className="brand">
        <a href="/">
          <img src="/media/icons/Logo.png" alt="Logo" />
        </a>
      </div>

      <div className="auth-actions">
        <Link className="btn-login" to="/app/login/">Login</Link>
        <Link className="btn-register" to="/app/register/">Register</Link>
      </div>
    </nav>
  );
}

export default NavbarLogin;
