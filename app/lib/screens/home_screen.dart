import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:shimmer/shimmer.dart';
import '../providers/auth_provider.dart';
import '../providers/dashboard_provider.dart';
import '../widgets/event_card.dart';
import '../widgets/task_card.dart';
import '../models/calendar_event.dart';

class HomeScreen extends ConsumerWidget {
  const HomeScreen({super.key});

  String _greeting() {
    final h = DateTime.now().hour;
    if (h < 12) return 'Guten Morgen';
    if (h < 18) return 'Guten Tag';
    return 'Guten Abend';
  }

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final authState = ref.watch(authProvider);
    final dashState = ref.watch(dashboardProvider);
    final user = authState.value ?? '';

    return Scaffold(
      appBar: AppBar(
        title: Text('${_greeting()}, ${user[0].toUpperCase()}${user.substring(1)}'),
        actions: [
          IconButton(icon: const Icon(Icons.refresh), onPressed: () => ref.invalidate(dashboardProvider)),
        ],
      ),
      body: dashState.when(
        loading: () => _buildSkeleton(),
        error: (e, _) => Center(child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            const Icon(Icons.wifi_off, size: 48, color: Colors.grey),
            const SizedBox(height: 16),
            Text('Keine Verbindung zur API', style: Theme.of(context).textTheme.titleMedium),
            const SizedBox(height: 8),
            FilledButton(onPressed: () => ref.invalidate(dashboardProvider), child: const Text('Erneut versuchen')),
          ],
        )),
        data: (data) => _buildContent(context, ref, data),
      ),
      floatingActionButton: FloatingActionButton.extended(
        onPressed: () => context.go('/chat'),
        icon: const Icon(Icons.chat),
        label: const Text('Chat'),
      ),
    );
  }

  Widget _buildContent(BuildContext context, WidgetRef ref, Map<String, dynamic> data) {
    final events = (data['events_today'] as List? ?? []).map((e) => CalendarEvent.fromJson(e as Map<String, dynamic>)).toList();
    final tasks = (data['open_tasks'] as List? ?? []);
    final shopping = data['shopping_preview'] as Map<String, dynamic>? ?? {};
    final unreadEmails = data['unread_emails'] as int? ?? 0;

    return RefreshIndicator(
      onRefresh: () async { ref.invalidate(dashboardProvider); },
      child: ListView(
        padding: const EdgeInsets.all(16),
        children: [
          if (unreadEmails > 0)
            Card(
              color: Colors.blue.shade900,
              child: ListTile(
                leading: const Icon(Icons.email, color: Colors.blue),
                title: Text('$unreadEmails ungelesene E-Mail${unreadEmails != 1 ? "s" : ""}'),
                trailing: const Icon(Icons.arrow_forward_ios, size: 14),
              ),
            ),
          const SizedBox(height: 8),

          _SectionHeader(title: 'Heute', icon: Icons.calendar_today),
          if (!(data['calendar_connected'] as bool? ?? false))
            const _DisabledHint(text: 'Google Calendar nicht verbunden')
          else if (events.isEmpty)
            const _EmptyHint(text: 'Keine Termine heute')
          else
            ...events.take(3).map((e) => EventCard(event: e)),

          const SizedBox(height: 16),
          _SectionHeader(title: 'Aufgaben (${data['task_count'] ?? 0})', icon: Icons.check_box_outlined),
          if (tasks.isEmpty)
            const _EmptyHint(text: 'Keine offenen Aufgaben')
          else
            ...tasks.take(3).map((t) => TaskCard(task: _taskFromMap(t as Map<String, dynamic>))),

          const SizedBox(height: 16),
          _SectionHeader(title: 'Einkauf', icon: Icons.shopping_cart_outlined),
          _ShoppingPreviewCard(data: shopping),
        ],
      ),
    );
  }

  Widget _buildSkeleton() {
    return Shimmer.fromColors(
      baseColor: Colors.grey.shade800,
      highlightColor: Colors.grey.shade700,
      child: ListView(
        padding: const EdgeInsets.all(16),
        children: List.generate(6, (_) => Container(
          margin: const EdgeInsets.symmetric(vertical: 6),
          height: 64,
          decoration: BoxDecoration(color: Colors.white, borderRadius: BorderRadius.circular(8)),
        )),
      ),
    );
  }

  dynamic _taskFromMap(Map<String, dynamic> m) {
    // Minimal Task for display
    return _MinimalTask(m);
  }
}

class _MinimalTask {
  final Map<String, dynamic> data;
  _MinimalTask(this.data);
  int get id => data['id'] as int? ?? 0;
  String get userKey => data['user_key'] as String? ?? '';
  String get title => data['title'] as String? ?? '';
  String get description => data['description'] as String? ?? '';
  String get priority => data['priority'] as String? ?? 'medium';
  String get status => data['status'] as String? ?? 'open';
  bool get isDone => status == 'done';
  DateTime? get dueDate => null;
  String? get assignedBy => null;
  DateTime get createdAt => DateTime.now();
  String get priorityLabel => priority;
}

class _SectionHeader extends StatelessWidget {
  final String title;
  final IconData icon;
  const _SectionHeader({required this.title, required this.icon});

  @override
  Widget build(BuildContext context) => Padding(
    padding: const EdgeInsets.only(bottom: 8),
    child: Row(children: [
      Icon(icon, size: 18, color: Theme.of(context).colorScheme.primary),
      const SizedBox(width: 8),
      Text(title, style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 15)),
    ]),
  );
}

class _EmptyHint extends StatelessWidget {
  final String text;
  const _EmptyHint({required this.text});
  @override
  Widget build(BuildContext context) => Padding(
    padding: const EdgeInsets.symmetric(vertical: 8),
    child: Text(text, style: const TextStyle(color: Colors.grey)),
  );
}

class _DisabledHint extends StatelessWidget {
  final String text;
  const _DisabledHint({required this.text});
  @override
  Widget build(BuildContext context) => Padding(
    padding: const EdgeInsets.symmetric(vertical: 8),
    child: Row(children: [
      const Icon(Icons.link_off, size: 14, color: Colors.grey),
      const SizedBox(width: 6),
      Text(text, style: const TextStyle(color: Colors.grey)),
    ]),
  );
}

class _ShoppingPreviewCard extends StatelessWidget {
  final Map<String, dynamic> data;
  const _ShoppingPreviewCard({required this.data});

  @override
  Widget build(BuildContext context) {
    final total = data['total'] as int? ?? 0;
    final pending = data['pending'] as int? ?? 0;
    if (total == 0) return const _EmptyHint(text: 'Einkaufsliste ist leer');
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(12),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text('$pending von $total offen', style: const TextStyle(fontWeight: FontWeight.bold)),
            const SizedBox(height: 8),
            LinearProgressIndicator(
              value: total > 0 ? (total - pending) / total : 0,
              backgroundColor: Colors.grey.shade700,
            ),
          ],
        ),
      ),
    );
  }
}
