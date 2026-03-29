import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import '../providers/auth_provider.dart';
import '../providers/dashboard_provider.dart';
import '../providers/features_provider.dart';

class ProfileScreen extends ConsumerWidget {
  const ProfileScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final authState = ref.watch(authProvider);
    final user = authState.value ?? '';
    final dashState = ref.watch(dashboardProvider);

    return Scaffold(
      appBar: AppBar(title: const Text('Profil')),
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

          // Einstellungen (Platzhalter)
          Text('Einstellungen', style: Theme.of(context).textTheme.titleMedium?.copyWith(fontWeight: FontWeight.bold)),
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
