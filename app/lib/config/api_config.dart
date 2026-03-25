/// API-Konfiguration
/// baseUrl wird beim ersten Start vom User gesetzt oder ist hardcoded für Dev.
class ApiConfig {
  /// Basis-URL der FastAPI. Im Produktivbetrieb IP/Domain des VPS.
  static const String baseUrl = String.fromEnvironment(
    'API_BASE_URL',
    defaultValue: 'http://localhost:8000',
  );

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
}
