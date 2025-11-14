import React from "react";
import "./ErrorPage.css";

export default function ErrorPage({ code = 404, message = "Page not Found" }) {
  return (
    <div className="error-container">
      <h1 className="error-code">{code}</h1>
      <p className="error-message">{message}</p>
    </div>
  );
}
