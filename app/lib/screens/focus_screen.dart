import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import '../providers/dashboard_provider.dart';

class FocusScreen extends ConsumerWidget {
  const FocusScreen({super.key});

  String _greeting() {
    final h = DateTime.now().hour;
    if (h < 12) return 'Guten Morgen';
    if (h < 18) return 'Guten Tag';
    return 'Guten Abend';
  }

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final dashState = ref.watch(dashboardProvider);
    final colorScheme = Theme.of(context).colorScheme;

    return Scaffold(
      appBar: AppBar(
        title: Text(_greeting()),
        actions: [
          IconButton(
            icon: const Icon(Icons.refresh),
            onPressed: () => ref.invalidate(dashboardProvider),
          ),
        ],
      ),
      body: dashState.when(
        loading: () => const Center(child: CircularProgressIndicator()),
        error: (e, _) => Center(
          child: Column(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              const Icon(Icons.wifi_off, size: 48, color: Colors.grey),
              const SizedBox(height: 16),
              const Text('Keine Verbindung'),
              const SizedBox(height: 8),
              FilledButton(
                onPressed: () => ref.invalidate(dashboardProvider),
                child: const Text('Erneut versuchen'),
              ),
            ],
          ),
        ),
        data: (data) => _buildContent(context, ref, data, colorScheme),
      ),
    );
  }

  Widget _buildContent(BuildContext context, WidgetRef ref, Map<String, dynamic> data, ColorScheme colorScheme) {
    final cards = <Widget>[];

    // 1. Next calendar event
    final events = data['events_today'] as List? ?? [];
    if (events.isNotEmpty) {
      final next = events.first as Map<String, dynamic>;
      cards.add(_FocusCard(
        icon: Icons.calendar_today,
        color: colorScheme.primary,
        title: 'Naechster Termin',
        subtitle: next['summary'] as String? ?? next['title'] as String? ?? 'Termin',
        detail: next['start_time'] as String?,
      ));
    }

    // 2. Top task
    final tasks = data['open_tasks'] as List? ?? [];
    if (tasks.isNotEmpty) {
      final top = tasks.first as Map<String, dynamic>;
      cards.add(_FocusCard(
        icon: Icons.check_box_outlined,
        color: Colors.orange,
        title: 'Wichtigste Aufgabe',
        subtitle: top['title'] as String? ?? 'Aufgabe',
        detail: top['priority'] as String?,
      ));
    }

    // 3. Shopping status
    final shopping = data['shopping_preview'] as Map<String, dynamic>?;
    if (shopping != null) {
      final total = shopping['total'] as int? ?? 0;
      final pending = shopping['pending'] as int? ?? 0;
      if (total > 0) {
        cards.add(_FocusCard(
          icon: Icons.shopping_cart_outlined,
          color: Colors.green,
          title: 'Einkaufsliste',
          subtitle: '$pending von $total offen',
        ));
      }
    }

    // 4. Unread emails
    final unreadEmails = data['unread_emails'] as int? ?? 0;
    if (unreadEmails > 0) {
      cards.add(_FocusCard(
        icon: Icons.email_outlined,
        color: Colors.blue,
        title: 'E-Mails',
        subtitle: '$unreadEmails ungelesen',
      ));
    }

    // 5. Weather
    final weather = data['weather'] as Map<String, dynamic>?;
    if (weather != null) {
      final temp = weather['temperature'] ?? weather['temp'];
      final desc = weather['description'] ?? weather['summary'] ?? '';
      cards.add(_FocusCard(
        icon: Icons.wb_sunny_outlined,
        color: Colors.amber,
        title: 'Wetter',
        subtitle: '$desc${temp != null ? ', $temp' : ''}',
      ));
    }

    if (cards.isEmpty) {
      cards.add(
        const Center(
          child: Padding(
            padding: EdgeInsets.all(32),
            child: Text('Alles erledigt!', style: TextStyle(fontSize: 18, color: Colors.grey)),
          ),
        ),
      );
    }

    return ListView(
      padding: const EdgeInsets.all(16),
      children: [
        ...cards.take(5),
        const SizedBox(height: 24),
        Center(
          child: TextButton.icon(
            onPressed: () => context.go('/home'),
            icon: const Icon(Icons.dashboard),
            label: const Text('Zum Dashboard'),
          ),
        ),
      ],
    );
  }
}

class _FocusCard extends StatelessWidget {
  final IconData icon;
  final Color color;
  final String title;
  final String subtitle;
  final String? detail;

  const _FocusCard({
    required this.icon,
    required this.color,
    required this.title,
    required this.subtitle,
    this.detail,
  });

  @override
  Widget build(BuildContext context) {
    return Card(
      margin: const EdgeInsets.symmetric(vertical: 6),
      child: Padding(
        padding: const EdgeInsets.all(20),
        child: Row(
          children: [
            Icon(icon, size: 36, color: color),
            const SizedBox(width: 16),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(title, style: const TextStyle(fontSize: 12, color: Colors.grey)),
                  const SizedBox(height: 4),
                  Text(subtitle, style: const TextStyle(fontSize: 18, fontWeight: FontWeight.bold)),
                  if (detail != null) ...[
                    const SizedBox(height: 2),
                    Text(detail!, style: const TextStyle(fontSize: 13, color: Colors.grey)),
                  ],
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }
}
