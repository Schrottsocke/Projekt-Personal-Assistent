import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../providers/inbox_provider.dart';
import '../models/inbox_item.dart';

class InboxScreen extends ConsumerStatefulWidget {
  const InboxScreen({super.key});
  @override
  ConsumerState<InboxScreen> createState() => _InboxScreenState();
}

class _InboxScreenState extends ConsumerState<InboxScreen> {
  String? _statusFilter;
  String? _categoryFilter;

  static const _statusFilters = [
    (null, 'Alle'),
    ('pending', 'Ausstehend'),
    ('approved', 'Genehmigt'),
    ('dismissed', 'Abgelehnt'),
    ('snoozed', 'Zurueckgestellt'),
  ];

  static const _categoryFilters = [
    (null, 'Alle'),
    ('proposal', 'Vorschlaege'),
    ('approval', 'Genehmigungen'),
    ('followup', 'Follow-ups'),
  ];

  @override
  Widget build(BuildContext context) {
    final state = ref.watch(inboxProvider);
    final colorScheme = Theme.of(context).colorScheme;

    return Scaffold(
      appBar: AppBar(
        title: const Text('Inbox'),
        actions: [
          IconButton(
            icon: const Icon(Icons.refresh),
            tooltip: 'Aktualisieren',
            onPressed: () => ref.read(inboxProvider.notifier).refresh(
              status: _statusFilter,
              category: _categoryFilter,
            ),
          ),
        ],
      ),
      body: Column(
        children: [
          SizedBox(
            height: 48,
            child: ListView(
              scrollDirection: Axis.horizontal,
              padding: const EdgeInsets.symmetric(horizontal: 12),
              children: [
                ..._statusFilters.map((f) {
                  final selected = _statusFilter == f.$1;
                  return Padding(
                    padding: const EdgeInsets.only(right: 8),
                    child: FilterChip(
                      label: Text(f.$2),
                      selected: selected,
                      onSelected: (_) {
                        setState(() => _statusFilter = selected ? null : f.$1);
                        ref.read(inboxProvider.notifier).refresh(
                          status: _statusFilter,
                          category: _categoryFilter,
                        );
                      },
                    ),
                  );
                }),
                const VerticalDivider(width: 16),
                ..._categoryFilters.map((f) {
                  final selected = _categoryFilter == f.$1;
                  return Padding(
                    padding: const EdgeInsets.only(right: 8),
                    child: FilterChip(
                      label: Text(f.$2),
                      selected: selected,
                      onSelected: (_) {
                        setState(() => _categoryFilter = selected ? null : f.$1);
                        ref.read(inboxProvider.notifier).refresh(
                          status: _statusFilter,
                          category: _categoryFilter,
                        );
                      },
                    ),
                  );
                }),
              ],
            ),
          ),
          Expanded(
            child: state.when(
              loading: () => const Center(child: CircularProgressIndicator()),
              error: (e, _) => Center(
                child: Column(
                  mainAxisAlignment: MainAxisAlignment.center,
                  children: [
                    const Icon(Icons.cloud_off, size: 48, color: Colors.grey),
                    const SizedBox(height: 16),
                    const Text('Inbox konnte nicht geladen werden'),
                    const SizedBox(height: 8),
                    FilledButton(
                      onPressed: () => ref.invalidate(inboxProvider),
                      child: const Text('Erneut versuchen'),
                    ),
                  ],
                ),
              ),
              data: (items) {
                if (items.isEmpty) {
                  return const Center(
                    child: Column(
                      mainAxisAlignment: MainAxisAlignment.center,
                      children: [
                        Icon(Icons.inbox_outlined, size: 48, color: Colors.grey),
                        SizedBox(height: 16),
                        Text('Keine Eintraege', style: TextStyle(color: Colors.grey)),
                      ],
                    ),
                  );
                }

                return RefreshIndicator(
                  onRefresh: () async => ref.read(inboxProvider.notifier).refresh(
                    status: _statusFilter,
                    category: _categoryFilter,
                  ),
                  child: ListView.builder(
                    padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 4),
                    itemCount: items.length,
                    itemBuilder: (_, i) => _InboxCard(
                      item: items[i],
                      colorScheme: colorScheme,
                      onAction: (action) async {
                        await ref.read(inboxProvider.notifier).performAction(items[i].id, action);
                      },
                    ),
                  ),
                );
              },
            ),
          ),
        ],
      ),
    );
  }
}

class _InboxCard extends StatelessWidget {
  final InboxItem item;
  final ColorScheme colorScheme;
  final Future<void> Function(String action) onAction;

  const _InboxCard({
    required this.item,
    required this.colorScheme,
    required this.onAction,
  });

  @override
  Widget build(BuildContext context) {
    return Card(
      margin: const EdgeInsets.symmetric(vertical: 4),
      child: Padding(
        padding: const EdgeInsets.all(12),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Expanded(
                  child: Text(item.title, style: const TextStyle(fontWeight: FontWeight.bold)),
                ),
                if (item.priority != null)
                  Container(
                    padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
                    decoration: BoxDecoration(
                      color: _priorityColor(item.priority!),
                      borderRadius: BorderRadius.circular(4),
                    ),
                    child: Text(
                      item.priority!,
                      style: const TextStyle(fontSize: 11, color: Colors.white),
                    ),
                  ),
              ],
            ),
            if (item.body != null) ...[
              const SizedBox(height: 4),
              Text(item.body!, style: const TextStyle(color: Colors.grey, fontSize: 13), maxLines: 2, overflow: TextOverflow.ellipsis),
            ],
            const SizedBox(height: 8),
            Wrap(
              spacing: 8,
              children: [
                if (item.actions.contains('approve'))
                  ActionChip(
                    label: const Text('Genehmigen'),
                    avatar: const Icon(Icons.check, size: 16),
                    onPressed: () => onAction('approve'),
                  ),
                if (item.actions.contains('snooze'))
                  ActionChip(
                    label: const Text('Zurueckstellen'),
                    avatar: const Icon(Icons.snooze, size: 16),
                    onPressed: () => onAction('snooze'),
                  ),
                if (item.actions.contains('dismiss'))
                  ActionChip(
                    label: const Text('Ablehnen'),
                    avatar: const Icon(Icons.close, size: 16),
                    onPressed: () => onAction('dismiss'),
                  ),
              ],
            ),
          ],
        ),
      ),
    );
  }

  Color _priorityColor(String p) {
    return switch (p) {
      'high' => Colors.red.shade400,
      'medium' => Colors.orange.shade400,
      'low' => Colors.green.shade400,
      _ => Colors.grey,
    };
  }
}
