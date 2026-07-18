/**
 * Chiavi delle chiavi di storage (localStorage) per lo stato di autenticazione.
 *
 * Centralizza i nomi delle chiavi usate dall'app per token, utente, refresh,
 * flag di login OAuth, errori ed eventuali reload a chunk: `bikemaster_token`,
 * `bikemaster_user`, `bikemaster_refresh_token`, `bikemaster_just_logged_in`,
 * `bikemaster_login_error`, `bikemaster_oauth_loading`, `bikemaster_chunk_reload_at`.
 */

export const AUTH_TOKEN_KEY = "bikemaster_token";
export const AUTH_USER_KEY = "bikemaster_user";
export const AUTH_JUST_LOGGED_IN_KEY = "bikemaster_just_logged_in";
export const AUTH_REFRESH_TOKEN_KEY = "bikemaster_refresh_token";
export const AUTH_LOGIN_ERROR_KEY = "bikemaster_login_error";
export const AUTH_OAUTH_LOADING_KEY = "bikemaster_oauth_loading";
export const AUTH_CHUNK_RELOAD_KEY = "bikemaster_chunk_reload_at";
