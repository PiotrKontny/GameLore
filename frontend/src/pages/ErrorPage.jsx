// src/pages/ErrorPage.jsx
import React from "react";
import { useLocation } from "react-router-dom";
import "./ErrorPage.css";

export default function ErrorPage({ code = 404, message }) {
  const location = useLocation();

  const defaultMessages = {
    400: "Bad Request",
    401: "Unauthorized",
    403: "Forbidden",
    404: "Page not Found",
    500: "Internal Server Error",
  };

  const finalMessage = message || defaultMessages[code] || "Unknown Error";

  let extra;
  if (code === 404) {
    extra = (
      <p className="error-description">
        The page <strong>{location.pathname}</strong> does not exist.
      </p>
    );
  } else if (code === 401) {
    extra = (
      <p className="error-description">
        Your session may have expired. Please log in again.
      </p>
    );
  } else if (code === 403) {
    extra = (
      <p className="error-description">
        You do not have permission to view this page.
      </p>
    );
  } else {
    extra = (
      <p className="error-description">
        An unexpected error occurred while loading{" "}
        <strong>{location.pathname}</strong>.
      </p>
    );
  }

  return (
    <div className="error-container">
      <h1 className="error-code">{code}</h1>
      <p className="error-message">{finalMessage}</p>
      {extra}
    </div>
  );
}
