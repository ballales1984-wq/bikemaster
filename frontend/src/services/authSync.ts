import { useAuthStore } from "../stores/auth";

export function syncAuthState() {
  const auth = useAuthStore();
  const hasLocalStorage = typeof localStorage !== "undefined";
  const storedToken = hasLocalStorage
    ? localStorage.getItem("bikemaster_token")
    : null;
  const storedJustLoggedIn = hasLocalStorage
    ? localStorage.getItem("bikemaster_just_logged_in") === "true"
    : false;

  if (hasLocalStorage && !auth.token && storedToken) {
    auth.token = storedToken;
  }
  if (
    hasLocalStorage &&
    !auth.user &&
    localStorage.getItem("bikemaster_user")
  ) {
    try {
      auth.user = JSON.parse(localStorage.getItem("bikemaster_user")!);
    } catch {}
  }
  if (!auth.justLoggedIn && storedJustLoggedIn) {
    auth.setJustLoggedIn(true);
  }

  if (auth.token && !auth.isTokenValid()) {
    auth.token = "";
    auth.user = null;
    localStorage.removeItem("bikemaster_token");
    localStorage.removeItem("bikemaster_user");
    auth.setJustLoggedIn(false);
    return { hasToken: false, justLoggedIn: false };
  }

  return { hasToken: !!auth.token, justLoggedIn: storedJustLoggedIn };
}
