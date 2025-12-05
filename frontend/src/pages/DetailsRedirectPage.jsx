import { useSearchParams, useNavigate } from "react-router-dom";
import React, { useEffect, useState } from "react";

export default function DetailsRedirectPage() {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const url = searchParams.get("url");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function load() {
      if (!url) return;

      // Pobieramy dane od Django
      const res = await fetch(`/app/details/?url=${encodeURIComponent(url)}&format=json`, {
        headers: { "x-requested-with": "XMLHttpRequest" }
      });

      const data = await res.json();

      if (data.redirect_game_id) {
        navigate(`/app/games/${data.redirect_game_id}`);
      } else if (data.redirect_compilation) {
        navigate(`/app/compilation/?url=${encodeURIComponent(url)}`);
      } else if (data.new_game_id) {
        navigate(`/app/games/${data.new_game_id}`);
      } else {
        console.error("Unexpected details API response:", data);
      }

      setLoading(false);
    }

    load();
  }, [url]);

  return (
  <div className="center-loader redirect-loader">
    <div className="spinner"></div>
    <span>Loading game details...</span>
  </div>
);
}
