import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import '../providers/auth_provider.dart';
import '../providers/dashboard_provider.dart';
import '../providers/features_provider.dart';
import '../providers/preferences_provider.dart';

class ProfileScreen extends ConsumerWidget {
  const ProfileScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final authState = ref.watch(authProvider);
    final user = authState.value ?? '';
    final dashState = ref.watch(dashboardProvider);

    return Scaffold(
      appBar: AppBar(title: const Text('Einstellungen')),
      body: ListView(
        padding: const EdgeInsets.all(16),
        children: [
          // Avatar
          Center(
            child: Column(
              children: [
                CircleAvatar(
                  radius: 40,
                  backgroundColor: Theme.of(context).colorScheme.primary,
                  child: Text(
                    user.isEmpty ? '?' : user[0].toUpperCase(),
                    style: const TextStyle(fontSize: 32, color: Colors.white, fontWeight: FontWeight.bold),
                  ),
                ),
                const SizedBox(height: 12),
                Text(user.isEmpty ? '' : user[0].toUpperCase() + user.substring(1),
                    style: Theme.of(context).textTheme.titleLarge?.copyWith(fontWeight: FontWeight.bold)),
                if (user.isNotEmpty) ...[
                  const SizedBox(height: 4),
                  Text(
                    '$user@dualmind.app',
                    style: Theme.of(context).textTheme.bodyMedium?.copyWith(color: Colors.grey),
                  ),
                ],
              ],
            ),
          ),
          const SizedBox(height: 32),

          // Navigation Config
          Text('Navigation', style: Theme.of(context).textTheme.titleMedium?.copyWith(fontWeight: FontWeight.bold)),
          const SizedBox(height: 4),
          Text('Bereiche aktivieren und in die Navbar pinnen (max. 5).', style: Theme.of(context).textTheme.bodySmall?.copyWith(color: Colors.grey)),
          const SizedBox(height: 8),
          const _NavConfigSection(),
          const SizedBox(height: 24),

          // Dashboard Widgets
          Text('Dashboard-Widgets', style: Theme.of(context).textTheme.titleMedium?.copyWith(fontWeight: FontWeight.bold)),
          const SizedBox(height: 4),
          Text('Widgets auf dem Home-Screen ein-/ausblenden.', style: Theme.of(context).textTheme.bodySmall?.copyWith(color: Colors.grey)),
          const SizedBox(height: 8),
          const _WidgetConfigSection(),
          const SizedBox(height: 24),

          // Feature-Marketplace
          Row(
            children: [
              Text('Features', style: Theme.of(context).textTheme.titleMedium?.copyWith(fontWeight: FontWeight.bold)),
              const SizedBox(width: 8),
              const Icon(Icons.storefront, size: 18),
            ],
          ),
          const SizedBox(height: 8),
          const _FeaturesSection(),
          const SizedBox(height: 32),

          // Dienste Status
          Text('Verbundene Dienste', style: Theme.of(context).textTheme.titleMedium?.copyWith(fontWeight: FontWeight.bold)),
          const SizedBox(height: 12),
          dashState.when(
            loading: () => const Center(child: CircularProgressIndicator()),
            error: (_, __) => const Text('Dienste nicht abrufbar', style: TextStyle(color: Colors.grey)),
            data: (data) => Column(
              children: [
                _ServiceTile(
                  icon: Icons.calendar_today,
                  name: 'Google Calendar',
                  connected: data['calendar_connected'] as bool? ?? false,
                ),
                _ServiceTile(
                  icon: Icons.email,
                  name: 'Gmail',
                  connected: data['email_connected'] as bool? ?? false,
                ),
              ],
            ),
          ),
          const SizedBox(height: 32),

          // Sonstige Einstellungen
          Text('Sonstige Einstellungen', style: Theme.of(context).textTheme.titleMedium?.copyWith(fontWeight: FontWeight.bold)),
          const SizedBox(height: 8),
          const ListTile(
            leading: Icon(Icons.schedule),
            title: Text('Briefing-Zeit'),
            subtitle: Text('08:00 Uhr'),
            dense: true,
          ),
          const ListTile(
            leading: Icon(Icons.language),
            title: Text('Zeitzone'),
            subtitle: Text('Europe/Berlin'),
            dense: true,
          ),
          const SizedBox(height: 32),

          // Logout
          OutlinedButton.icon(
            onPressed: () async {
              final ok = await showDialog<bool>(
                context: context,
                builder: (_) => AlertDialog(
                  title: const Text('Abmelden?'),
                  content: const Text('Du wirst aus der App abgemeldet.'),
                  actions: [
                    TextButton(onPressed: () => Navigator.pop(context, false), child: const Text('Abbrechen')),
                    FilledButton(onPressed: () => Navigator.pop(context, true), child: const Text('Abmelden')),
                  ],
                ),
              );
              if (ok == true) {
                await ref.read(authProvider.notifier).logout();
                if (context.mounted) context.go('/login');
              }
            },
            icon: const Icon(Icons.logout),
            label: const Text('Abmelden'),
            style: OutlinedButton.styleFrom(foregroundColor: Colors.red),
          ),
        ],
      ),
    );
  }
}

// ── Nav Configuration Section ──

class _NavConfigSection extends ConsumerWidget {
  const _NavConfigSection();

  static const _navMeta = {
    'dashboard': {'label': 'Home', 'icon': Icons.home},
    'shopping': {'label': 'Einkauf', 'icon': Icons.shopping_cart},
    'recipes': {'label': 'Rezepte', 'icon': Icons.restaurant_menu},
    'chat': {'label': 'Chat', 'icon': Icons.chat_bubble},
    'profile': {'label': 'Profil', 'icon': Icons.person},
    'calendar': {'label': 'Kalender', 'icon': Icons.calendar_today},
    'tasks': {'label': 'Aufgaben', 'icon': Icons.check_circle},
    'mealplan': {'label': 'Wochenplan', 'icon': Icons.restaurant},
    'drive': {'label': 'Drive', 'icon': Icons.folder},
    'shifts': {'label': 'Dienste', 'icon': Icons.work},
    'issues': {'label': 'Issues', 'icon': Icons.bug_report},
  };

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final state = ref.watch(preferencesProvider);
    return state.when(
      loading: () => const Center(child: CircularProgressIndicator()),
      error: (e, _) => const Text('Nicht abrufbar', style: TextStyle(color: Colors.grey)),
      data: (prefs) {
        final nav = prefs['nav'] as Map<String, dynamic>? ?? {};
        final items = (nav['items'] as List<dynamic>? ?? []).cast<Map<String, dynamic>>();
        final maxPinned = nav['maxPinned'] as int? ?? 5;
        items.sort((a, b) => ((a['order'] as int?) ?? 0).compareTo((b['order'] as int?) ?? 0));

        final pinnedCount = items.where((i) => i['enabled'] == true && i['pinned'] == true).length;

        return Column(
          children: items.map((item) {
            final id = item['id'] as String;
            final meta = _navMeta[id];
            final label = meta?['label'] as String? ?? id;
            final icon = meta?['icon'] as IconData? ?? Icons.circle;
            final enabled = item['enabled'] as bool? ?? true;
            final pinned = item['pinned'] as bool? ?? false;

            return Card(
              margin: const EdgeInsets.symmetric(vertical: 2),
              child: ListTile(
                dense: true,
                leading: Icon(icon, size: 20, color: enabled ? null : Colors.grey),
                title: Text(label, style: TextStyle(color: enabled ? null : Colors.grey)),
                trailing: Row(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    // Pin toggle
                    IconButton(
                      icon: Icon(
                        pinned ? Icons.push_pin : Icons.push_pin_outlined,
                        color: pinned ? Theme.of(context).colorScheme.primary : Colors.grey,
                        size: 20,
                      ),
                      tooltip: pinned ? 'Aus Navbar entfernen' : 'In Navbar pinnen',
                      onPressed: enabled && (pinned || pinnedCount < maxPinned)
                          ? () => _toggleItem(ref, items, id, 'pinned', !pinned)
                          : null,
                    ),
                    // Enable toggle
                    Switch(
                      value: enabled,
                      onChanged: (val) => _toggleItem(ref, items, id, 'enabled', val),
                    ),
                  ],
                ),
              ),
            );
          }).toList(),
        );
      },
    );
  }

  Future<void> _toggleItem(WidgetRef ref, List<Map<String, dynamic>> items, String id, String field, bool value) async {
    final updated = items.map((i) {
      if (i['id'] != id) return Map<String, dynamic>.from(i);
      final copy = Map<String, dynamic>.from(i);
      copy[field] = value;
      if (field == 'enabled' && !value) copy['pinned'] = false;
      return copy;
    }).toList();

    await ref.read(preferencesProvider.notifier).updatePreferences({'nav': {'items': updated}});
  }
}

// ── Dashboard Widget Configuration Section ──

class _WidgetConfigSection extends ConsumerWidget {
  const _WidgetConfigSection();

  static const _widgetMeta = {
    'emails': {'label': 'E-Mails', 'icon': Icons.mail},
    'shifts': {'label': 'Dienste heute', 'icon': Icons.work},
    'events': {'label': 'Termine heute', 'icon': Icons.calendar_today},
    'tasks': {'label': 'Offene Aufgaben', 'icon': Icons.check_circle},
    'shopping': {'label': 'Einkaufsliste', 'icon': Icons.shopping_cart},
    'mealplan': {'label': 'Wochenplan', 'icon': Icons.restaurant},
    'drive': {'label': 'Drive', 'icon': Icons.folder},
  };

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final state = ref.watch(preferencesProvider);
    return state.when(
      loading: () => const Center(child: CircularProgressIndicator()),
      error: (e, _) => const Text('Nicht abrufbar', style: TextStyle(color: Colors.grey)),
      data: (prefs) {
        final dashboard = prefs['dashboard'] as Map<String, dynamic>? ?? {};
        final widgets = (dashboard['widgets'] as List<dynamic>? ?? []).cast<Map<String, dynamic>>();
        widgets.sort((a, b) => ((a['order'] as int?) ?? 0).compareTo((b['order'] as int?) ?? 0));

        return Column(
          children: widgets.map((w) {
            final id = w['id'] as String;
            final meta = _widgetMeta[id];
            final label = meta?['label'] as String? ?? id;
            final icon = meta?['icon'] as IconData? ?? Icons.widgets;
            final enabled = w['enabled'] as bool? ?? true;

            return SwitchListTile(
              dense: true,
              secondary: Icon(icon, size: 20),
              title: Text(label),
              value: enabled,
              onChanged: (val) async {
                final updated = widgets.map((item) {
                  if (item['id'] != id) return Map<String, dynamic>.from(item);
                  final copy = Map<String, dynamic>.from(item);
                  copy['enabled'] = val;
                  return copy;
                }).toList();
                await ref.read(preferencesProvider.notifier).updatePreferences({'dashboard': {'widgets': updated}});
              },
            );
          }).toList(),
        );
      },
    );
  }
}

// ── Features Section (unchanged) ──

class _FeaturesSection extends ConsumerWidget {
  const _FeaturesSection();

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final state = ref.watch(featuresProvider);
    return state.when(
      loading: () => const Center(child: CircularProgressIndicator()),
      error: (e, _) => const Text('Features nicht abrufbar', style: TextStyle(color: Colors.grey)),
      data: (features) => Column(
        children: features.map((feat) {
          final available = feat['available'] as bool? ?? false;
          final enabled = feat['enabled'] as bool? ?? false;
          return SwitchListTile(
            dense: true,
            secondary: Text(feat['emoji'] as String? ?? '•', style: const TextStyle(fontSize: 20)),
            title: Text(feat['name'] as String? ?? ''),
            subtitle: Text(
              available ? (feat['description'] as String? ?? '') : '⚠️ API-Keys fehlen',
              style: TextStyle(fontSize: 12, color: available ? null : Colors.orange),
            ),
            value: enabled,
            onChanged: available
                ? (val) async {
                    await ref.read(featuresProvider.notifier).toggle(feat['id'] as String);
                  }
                : null,
          );
        }).toList(),
      ),
    );
  }
}

// ── Service Status Tile ──

class _ServiceTile extends StatelessWidget {
  final IconData icon;
  final String name;
  final bool connected;
  const _ServiceTile({required this.icon, required this.name, required this.connected});

  @override
  Widget build(BuildContext context) => ListTile(
        leading: Icon(icon),
        title: Text(name),
        trailing: Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(connected ? Icons.check_circle : Icons.cancel, color: connected ? Colors.green : Colors.red.shade400, size: 20),
            const SizedBox(width: 4),
            Text(connected ? 'Verbunden' : 'Nicht verbunden', style: TextStyle(fontSize: 12, color: connected ? Colors.green : Colors.red.shade400)),
          ],
        ),
        dense: true,
      );
}
