import { useAuthStore } from "../stores/auth";
import { useUIStore } from "../stores/ui";

export function processOAuthToken() {
  const auth = useAuthStore();
  const ui = useUIStore();
  const urlParams = new URLSearchParams(window.location.search);
  const hashParams = new URLSearchParams(
    window.location.hash.replace(/^#/, ""),
  );
  const urlToken = urlParams.get("token") || hashParams.get("token");
  const email = urlParams.get("email") || hashParams.get("email") || "";
  const userId = urlParams.get("user_id") || hashParams.get("user_id") || "";
  const oauthError =
    urlParams.get("oauth_error") || hashParams.get("oauth_error");

  if (oauthError) {
    auth.setOauthError(oauthError);
    ui.setOauthLoading(false);
    if (window.history.replaceState) {
      window.history.replaceState({}, document.title, "/");
    }
    return true;
  }

  if (urlToken) {
    if (auth.isLoggedIn && auth.isTokenValid()) {
      ui.setOauthLoading(false);
      if (window.history.replaceState) {
        window.history.replaceState({}, document.title, "/");
      }
      return false;
    }
    auth.setAuthFromUrl(urlToken, email, userId);
    // Clear the overlay here too: the spinner was turned on by LoginForm and
    // relying solely on the router guard / finalizeOAuthReturn to clear it left
    // a window where a failure downstream would strand the user on the spinner.
    ui.setOauthLoading(false);
    if (window.history.replaceState) {
      window.history.replaceState({}, document.title, "/");
    }
    return true;
  }

  return false;
}
