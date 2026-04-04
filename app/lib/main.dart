import 'dart:async';

import 'package:flutter/foundation.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'providers/auth_provider.dart';
import 'providers/preferences_provider.dart';
import 'screens/login_screen.dart';
import 'screens/home_screen.dart';
import 'screens/shopping_screen.dart';
import 'screens/recipes_screen.dart';
import 'screens/chat_screen.dart';
import 'screens/profile_screen.dart';
import 'screens/tasks_screen.dart';
import 'screens/calendar_screen.dart';
import 'screens/mealplan_screen.dart';
import 'screens/notifications_screen.dart';
import 'providers/theme_provider.dart';
import 'screens/weather_screen.dart';
import 'screens/drive_screen.dart';
import 'screens/shifts_screen.dart';
import 'screens/contacts_screen.dart';
import 'screens/followups_screen.dart';
import 'screens/documents_screen.dart';
import 'screens/search_screen.dart';
import 'screens/templates_screen.dart';
import 'screens/automation_screen.dart';
import 'screens/inbox_screen.dart';
import 'screens/memory_screen.dart';
import 'screens/mobility_screen.dart';
import 'screens/focus_screen.dart';
import 'screens/issues_screen.dart';

void main() {
  FlutterError.onError = (details) {
    FlutterError.presentError(details);
    debugPrint('FlutterError: ${details.exceptionAsString()}');
  };

  ErrorWidget.builder = (details) {
    if (kReleaseMode) {
      return const Center(
        child: Text(
          'Ein unerwarteter Fehler ist aufgetreten.',
          style: TextStyle(color: Colors.grey),
        ),
      );
    }
    return ErrorWidget(details.exception);
  };

  runZonedGuarded(
    () => runApp(const ProviderScope(child: DualMindApp())),
    (error, stack) {
      debugPrint('Unhandled error: $error\n$stack');
    },
  );
}

/// Registry of all navigable areas with their metadata.
class NavArea {
  final String id;
  final String path;
  final String label;
  final IconData icon;
  final IconData selectedIcon;
  final Widget screen;

  const NavArea({
    required this.id,
    required this.path,
    required this.label,
    required this.icon,
    required this.selectedIcon,
    required this.screen,
  });
}

/// All available nav areas. Order here is irrelevant – preferences control the order.
final List<NavArea> allNavAreas = [
  NavArea(id: 'dashboard', path: '/home', label: 'Home', icon: Icons.home_outlined, selectedIcon: Icons.home, screen: const HomeScreen()),
  NavArea(id: 'shopping', path: '/shopping', label: 'Einkauf', icon: Icons.shopping_cart_outlined, selectedIcon: Icons.shopping_cart, screen: const ShoppingScreen()),
  NavArea(id: 'recipes', path: '/recipes', label: 'Rezepte', icon: Icons.restaurant_menu_outlined, selectedIcon: Icons.restaurant_menu, screen: const RecipesScreen()),
  NavArea(id: 'chat', path: '/chat', label: 'Chat', icon: Icons.chat_bubble_outline, selectedIcon: Icons.chat_bubble, screen: const ChatScreen()),
  NavArea(id: 'tasks', path: '/tasks', label: 'Aufgaben', icon: Icons.check_box_outlined, selectedIcon: Icons.check_box, screen: const TasksScreen()),
  NavArea(id: 'calendar', path: '/calendar', label: 'Kalender', icon: Icons.calendar_today_outlined, selectedIcon: Icons.calendar_today, screen: const CalendarScreen()),
  NavArea(id: 'mealplan', path: '/mealplan', label: 'Wochenplan', icon: Icons.restaurant_outlined, selectedIcon: Icons.restaurant, screen: const MealPlanScreen()),
  NavArea(id: 'notifications', path: '/notifications', label: 'Mitteilungen', icon: Icons.notifications_outlined, selectedIcon: Icons.notifications, screen: const NotificationsScreen()),
  NavArea(id: 'weather', path: '/weather', label: 'Wetter', icon: Icons.wb_sunny_outlined, selectedIcon: Icons.wb_sunny, screen: const WeatherScreen()),
  NavArea(id: 'drive', path: '/drive', label: 'Drive', icon: Icons.folder_outlined, selectedIcon: Icons.folder, screen: const DriveScreen()),
  NavArea(id: 'shifts', path: '/shifts', label: 'Dienste', icon: Icons.work_outline, selectedIcon: Icons.work, screen: const ShiftsScreen()),
  NavArea(id: 'contacts', path: '/contacts', label: 'Kontakte', icon: Icons.contacts_outlined, selectedIcon: Icons.contacts, screen: const ContactsScreen()),
  NavArea(id: 'followups', path: '/followups', label: 'Follow-ups', icon: Icons.fact_check_outlined, selectedIcon: Icons.fact_check, screen: const FollowUpsScreen()),
  NavArea(id: 'documents', path: '/documents', label: 'Dokumente', icon: Icons.description_outlined, selectedIcon: Icons.description, screen: const DocumentsScreen()),
  NavArea(id: 'search', path: '/search', label: 'Suche', icon: Icons.search_outlined, selectedIcon: Icons.search, screen: const SearchScreen()),
  NavArea(id: 'profile', path: '/profile', label: 'Profil', icon: Icons.person_outline, selectedIcon: Icons.person, screen: const ProfileScreen()),
  NavArea(id: 'templates', path: '/templates', label: 'Vorlagen', icon: Icons.copy_outlined, selectedIcon: Icons.copy, screen: const TemplatesScreen()),
  NavArea(id: 'automations', path: '/automations', label: 'Automation', icon: Icons.auto_fix_high_outlined, selectedIcon: Icons.auto_fix_high, screen: const AutomationScreen()),
  NavArea(id: 'inbox', path: '/inbox', label: 'Inbox', icon: Icons.inbox_outlined, selectedIcon: Icons.inbox, screen: const InboxScreen()),
  NavArea(id: 'memory', path: '/memory', label: 'Gedaechtnis', icon: Icons.psychology_outlined, selectedIcon: Icons.psychology, screen: const MemoryScreen()),
  NavArea(id: 'mobility', path: '/mobility', label: 'Mobilitaet', icon: Icons.directions_car_outlined, selectedIcon: Icons.directions_car, screen: const MobilityScreen()),
  NavArea(id: 'focus', path: '/focus', label: 'Fokus', icon: Icons.center_focus_strong_outlined, selectedIcon: Icons.center_focus_strong, screen: const FocusScreen()),
  NavArea(id: 'issues', path: '/issues', label: 'Issues', icon: Icons.bug_report_outlined, selectedIcon: Icons.bug_report, screen: const IssuesScreen()),
];

/// Default pinned nav IDs (used before preferences load).
const List<String> defaultPinnedIds = ['dashboard', 'shopping', 'recipes', 'chat', 'profile'];

class DualMindApp extends ConsumerWidget {
  const DualMindApp({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final prefsState = ref.watch(preferencesProvider);
    final pinnedIds = _getPinnedIds(prefsState);
    final router = _buildRouter(ref, pinnedIds);

    final themeMode = ref.watch(themeModeProvider);

    final darkTheme = ThemeData(
      useMaterial3: true,
      colorScheme: ColorScheme.fromSeed(
        seedColor: const Color(0xFF1565C0),
        brightness: Brightness.dark,
      ),
    );

    final lightTheme = ThemeData(
      useMaterial3: true,
      colorScheme: ColorScheme.fromSeed(
        seedColor: const Color(0xFF1565C0),
        brightness: Brightness.light,
      ),
    );

    return MaterialApp.router(
      title: 'DualMind',
      debugShowCheckedModeBanner: false,
      theme: lightTheme,
      darkTheme: darkTheme,
      themeMode: themeMode,
      routerConfig: router,
    );
  }

  /// Extracts the ordered list of pinned nav area IDs from preferences.
  List<String> _getPinnedIds(AsyncValue<Map<String, dynamic>> prefsState) {
    return prefsState.when(
      data: (prefs) {
        final nav = prefs['nav'] as Map<String, dynamic>?;
        if (nav == null) return defaultPinnedIds;
        final items = nav['items'] as List<dynamic>?;
        if (items == null || items.isEmpty) return defaultPinnedIds;

        final pinned = items
            .where((i) => i['enabled'] == true && i['pinned'] == true)
            .toList()
          ..sort((a, b) => ((a['order'] as int?) ?? 0).compareTo((b['order'] as int?) ?? 0));

        final ids = pinned.map((i) => i['id'] as String).toList();
        return ids.isNotEmpty ? ids : defaultPinnedIds;
      },
      loading: () => defaultPinnedIds,
      error: (_, __) => defaultPinnedIds,
    );
  }

  GoRouter _buildRouter(WidgetRef ref, List<String> pinnedIds) {
    // Build branches from pinned IDs, matching against allNavAreas
    final navAreas = <NavArea>[];
    for (final id in pinnedIds) {
      final area = allNavAreas.where((a) => a.id == id).firstOrNull;
      if (area != null) navAreas.add(area);
    }
    // Ensure at least defaults if nothing matched
    if (navAreas.isEmpty) {
      for (final id in defaultPinnedIds) {
        final area = allNavAreas.where((a) => a.id == id).firstOrNull;
        if (area != null) navAreas.add(area);
      }
    }

    return GoRouter(
      initialLocation: '/home',
      redirect: (context, state) {
        final authState = ref.read(authProvider);
        final loggedIn = authState.value != null && authState.value!.isNotEmpty;
        final onLogin = state.matchedLocation == '/login';

        if (!loggedIn && !onLogin) return '/login';
        if (loggedIn && onLogin) return '/home';
        return null;
      },
      refreshListenable: _AuthListenable(ref),
      routes: [
        GoRoute(
          path: '/login',
          builder: (_, __) => const LoginScreen(),
        ),
        StatefulShellRoute.indexedStack(
          builder: (context, state, navigationShell) =>
              _ScaffoldWithBottomNav(navigationShell: navigationShell, navAreas: navAreas),
          branches: navAreas.map((area) => StatefulShellBranch(routes: [
            GoRoute(path: area.path, builder: (_, __) => area.screen),
          ])).toList(),
        ),
      ],
    );
  }
}

class _AuthListenable extends ChangeNotifier {
  _AuthListenable(WidgetRef ref) {
    ref.listen(authProvider, (_, __) => notifyListeners());
  }
}

class _ScaffoldWithBottomNav extends StatelessWidget {
  final StatefulNavigationShell navigationShell;
  final List<NavArea> navAreas;
  const _ScaffoldWithBottomNav({required this.navigationShell, required this.navAreas});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: navigationShell,
      bottomNavigationBar: NavigationBar(
        selectedIndex: navigationShell.currentIndex,
        onDestinationSelected: (i) => navigationShell.goBranch(
          i,
          initialLocation: i == navigationShell.currentIndex,
        ),
        destinations: navAreas.map((area) => NavigationDestination(
          icon: Icon(area.icon),
          selectedIcon: Icon(area.selectedIcon),
          label: area.label,
        )).toList(),
      ),
    );
  }
}
