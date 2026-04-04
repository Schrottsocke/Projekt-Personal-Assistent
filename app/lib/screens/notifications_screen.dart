import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../models/notification_item.dart';
import '../providers/notification_provider.dart';

class NotificationsScreen extends ConsumerStatefulWidget {
  const NotificationsScreen({super.key});

  @override
  ConsumerState<NotificationsScreen> createState() => _NotificationsScreenState();
}

class _NotificationsScreenState extends ConsumerState<NotificationsScreen> {
  String _filter = 'all'; // all, unread, read, archived

  @override
  Widget build(BuildContext context) {
    final state = ref.watch(notificationProvider);

    return Scaffold(
      appBar: AppBar(
        title: const Text('Mitteilungen'),
        actions: [
          IconButton(
            icon: const Icon(Icons.done_all),
            tooltip: 'Alle als gelesen markieren',
            onPressed: () async {
              await ref.read(notificationProvider.notifier).markAllRead();
            },
          ),
        ],
      ),
      body: Column(
        children: [
          // Filter chips
          SingleChildScrollView(
            scrollDirection: Axis.horizontal,
            padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
            child: Row(
              children: [
                _filterChip('all', 'Alle'),
                const SizedBox(width: 8),
                _filterChip('unread', 'Ungelesen'),
                const SizedBox(width: 8),
                _filterChip('read', 'Gelesen'),
                const SizedBox(width: 8),
                _filterChip('archived', 'Archiviert'),
              ],
            ),
          ),
          const Divider(height: 1),
          // List
          Expanded(
            child: state.when(
              loading: () => const Center(child: CircularProgressIndicator()),
              error: (e, _) => Center(child: Text('Fehler: $e')),
              data: (items) {
                final filtered = _filter == 'all'
                    ? items.where((i) => i.status != 'archived').toList()
                    : items.where((i) => i.status == _filter).toList();

                if (filtered.isEmpty) {
                  return Center(
                    child: Column(
                      mainAxisSize: MainAxisSize.min,
                      children: [
                        Icon(Icons.notifications_none, size: 64, color: Colors.grey.withValues(alpha: 0.5)),
                        const SizedBox(height: 12),
                        const Text('Keine Mitteilungen', style: TextStyle(color: Colors.grey)),
                      ],
                    ),
                  );
                }

                return RefreshIndicator(
                  onRefresh: () => ref.read(notificationProvider.notifier).refresh(),
                  child: ListView.builder(
                    itemCount: filtered.length,
                    itemBuilder: (context, index) => _buildTile(context, filtered[index]),
                  ),
                );
              },
            ),
          ),
        ],
      ),
    );
  }

  Widget _filterChip(String value, String label) {
    final selected = _filter == value;
    return FilterChip(
      label: Text(label),
      selected: selected,
      onSelected: (_) => setState(() => _filter = value),
    );
  }

  Widget _buildTile(BuildContext context, NotificationItem item) {
    return Dismissible(
      key: ValueKey(item.id),
      background: Container(
        color: Colors.blue,
        alignment: Alignment.centerLeft,
        padding: const EdgeInsets.only(left: 20),
        child: const Icon(Icons.mark_email_read, color: Colors.white),
      ),
      secondaryBackground: Container(
        color: Colors.orange,
        alignment: Alignment.centerRight,
        padding: const EdgeInsets.only(right: 20),
        child: const Icon(Icons.archive, color: Colors.white),
      ),
      confirmDismiss: (direction) async {
        if (direction == DismissDirection.startToEnd) {
          await ref.read(notificationProvider.notifier).markRead(item.id);
        } else {
          await ref.read(notificationProvider.notifier).archive(item.id);
        }
        return false; // Don't remove widget, refresh handles it
      },
      child: ListTile(
        leading: _typeIcon(item.type),
        title: Text(
          item.title,
          style: TextStyle(
            fontWeight: item.status == 'unread' ? FontWeight.bold : FontWeight.normal,
          ),
        ),
        subtitle: item.body != null
            ? Text(item.body!, maxLines: 2, overflow: TextOverflow.ellipsis)
            : null,
        trailing: Text(
          _formatTime(item.createdAt),
          style: Theme.of(context).textTheme.bodySmall?.copyWith(color: Colors.grey),
        ),
        dense: true,
      ),
    );
  }

  Widget _typeIcon(String type) {
    switch (type) {
      case 'warning':
        return const Icon(Icons.warning_amber, color: Colors.orange);
      case 'success':
        return const Icon(Icons.check_circle, color: Colors.green);
      case 'error':
        return const Icon(Icons.error, color: Colors.red);
      default:
        return const Icon(Icons.info, color: Colors.blue);
    }
  }

  String _formatTime(DateTime dt) {
    final now = DateTime.now();
    final diff = now.difference(dt);
    if (diff.inMinutes < 60) return 'vor ${diff.inMinutes}m';
    if (diff.inHours < 24) return 'vor ${diff.inHours}h';
    if (diff.inDays < 7) return 'vor ${diff.inDays}d';
    return '${dt.day}.${dt.month}.${dt.year}';
  }
}
