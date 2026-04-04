/// API-Konfiguration fuer DualMind Personal Assistant.
///
/// Die [baseUrl] wird ueber `--dart-define` zur Build-Zeit gesetzt.
/// Ohne explizite Angabe wird der lokale Entwicklungsserver verwendet.
///
/// ## Umgebungen
///
/// | Umgebung    | URL                                          | Hinweis                        |
/// |-------------|----------------------------------------------|--------------------------------|
/// | Development | `http://localhost:8000`                       | Default, kein Flag noetig      |
/// | Production  | `https://dualmind.cloud`                      | Muss per `--dart-define` gesetzt werden |
///
/// ## Konfiguration per --dart-define
///
/// ```sh
/// # Entwicklung (Standard – localhost:8000):
/// flutter run
///
/// # Produktion:
/// flutter run --dart-define=API_BASE_URL=https://dualmind.cloud
///
/// # APK fuer Produktion bauen:
/// flutter build apk --dart-define=API_BASE_URL=https://dualmind.cloud
/// ```
class ApiConfig {
  /// Basis-URL der FastAPI.
  ///
  /// Wird zur Compile-Zeit ueber `--dart-define=API_BASE_URL=...` injiziert.
  /// Fallback: `http://localhost:8000` (lokaler Dev-Server).
  static const String baseUrl = String.fromEnvironment(
    'API_BASE_URL',
    defaultValue: 'http://localhost:8000',
  );

  /// Produktions-URL-Muster. Beim Deployment die eigene Domain einsetzen.
  /// Beispiel: `https://dualmind.cloud`
  static const String prodBaseUrl = String.fromEnvironment(
    'API_PROD_URL',
    defaultValue: 'https://dualmind.cloud',
  );

  /// Gibt `true` zurueck, wenn die App gegen den Produktionsserver laeuft.
  static bool get isProduction => baseUrl != 'http://localhost:8000';

  static const Duration connectTimeout = Duration(seconds: 10);
  static const Duration receiveTimeout = Duration(seconds: 30);

  static const String loginPath = '/auth/login';
  static const String refreshPath = '/auth/refresh';
  static const String dashboardPath = '/dashboard/today';
  static const String chatMessagePath = '/chat/message';
  static const String chatHistoryPath = '/chat/history';
  static const String tasksPath = '/tasks';
  static const String calendarTodayPath = '/calendar/today';
  static const String calendarWeekPath = '/calendar/week';
  static const String calendarEventsPath = '/calendar/events';
  static const String shoppingItemsPath = '/shopping/items';
  static const String shoppingFromRecipePath = '/shopping/from-recipe';
  static const String recipesSearchPath = '/recipes/search';
  static const String recipesSavedPath = '/recipes/saved';
  static const String mealPlanWeekPath = '/meal-plan/week';
  static const String mealPlanPath = '/meal-plan';
  static const String driveFilesPath = '/drive/files';
  static const String driveUploadPath = '/drive/upload';
  static const String preferencesPath = '/preferences';
  static const String preferencesRegistryPath = '/preferences/registry';
  static const String contactsPath = '/contacts';
  static const String followupsPath = '/followups';
  static const String followupsDuePath = '/followups/due';
  static const String weatherCurrentPath = '/weather/current';
  static const String weatherForecastPath = '/weather/forecast';
  static const String weatherSimplePath = '/weather/simple';
  static const String mobilityTravelTimePath = '/mobility/travel-time';
  static const String mobilityDepartureTimePath = '/mobility/departure-time';
  static const String mobilityDailyFlowPath = '/mobility/daily-flow';
  static const String syncStatusPath = '/sync/status';
  static const String syncBatchPath = '/sync/batch';
  static const String notificationsPath = '/notifications';
  static const String notificationsCountPath = '/notifications/count';
  static const String notificationsMarkAllReadPath = '/notifications/mark-all-read';
  static const String chatStreamPath = '/chat/message/stream';
  static const String chatVoicePath = '/chat/voice';
  static const String chatSuggestionsPath = '/suggestions/chat';
  static const String shiftTypesPath = '/shifts/types';
  static const String shiftEntriesPath = '/shifts/entries';
  static const String documentsPath = '/documents';
  static const String documentsUploadPath = '/documents/upload';
  static const String searchPath = '/search';
  static const String templatesPath = '/templates';
  static const String automationsPath = '/automations';
  static const String inboxPath = '/inbox';
  static const String memoryPath = '/memory';
  static const String githubIssuesPath = '/github/issues';
  static const String githubLabelsPath = '/github/labels';
}
