// Entrypoint Tauri per la versione Desktop di BikeMaster.
//
// Il frontend Vue 3 gira nella webview e usa il layer SQLite WASM locale
// (src/db/localDb.ts) per la cache offline. Il backend (calcoli, dati) risiede
// sul PC dell'utente e viene contattato tramite l'URL configurabile nelle
// Impostazioni (default: fallisce su Render).
#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    tauri::Builder::default()
        .run(tauri::generate_context!())
        .expect("errore durante l'avvio dell'applicazione Tauri");
}
