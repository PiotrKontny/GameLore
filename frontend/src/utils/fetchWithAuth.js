import { navigate } from "./navigateGlobal";

export async function fetchWithAuth(url, options = {}) {
  const mergedOptions = {
    credentials: "include",
    ...options,
    headers: {
      "x-requested-with": "XMLHttpRequest",
      Accept: "application/json",
      ...(options.headers || {}),
    },
  };

  let resp = await fetch(url, mergedOptions);

  if (resp.status === 401) {
    const refresh = await fetch("/app/api/refresh/", {
      method: "POST",
      credentials: "include",
      headers: {
        "x-requested-with": "XMLHttpRequest",
        Accept: "application/json",
      },
    });

    if (refresh.status === 200) {
      resp = await fetch(url, mergedOptions);
      if (resp.status !== 401 && resp.status !== 403) {
        return resp;
      }
    }

    navigate("/error/401");
    return null;
  }

  if (resp.status === 403) {
    navigate("/error/403");
    return null;
  }

  return resp;
}
