import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:intl/intl.dart';
import '../models/followup.dart';
import '../providers/followup_provider.dart';

class FollowUpsScreen extends ConsumerStatefulWidget {
  const FollowUpsScreen({super.key});
  @override
  ConsumerState<FollowUpsScreen> createState() => _FollowUpsScreenState();
}

class _FollowUpsScreenState extends ConsumerState<FollowUpsScreen> {
  String _filter = 'open'; // open, done, cancelled, all

  @override
  Widget build(BuildContext context) {
    final state = ref.watch(followUpProvider);

    return Scaffold(
      appBar: AppBar(
        title: const Text('Follow-ups'),
        actions: [
          IconButton(
            icon: const Icon(Icons.refresh),
            tooltip: 'Aktualisieren',
            onPressed: () => ref.read(followUpProvider.notifier).refresh(),
          ),
        ],
      ),
      body: Column(
        children: [
          _buildFilterChips(),
          Expanded(
            child: state.when(
              loading: () => const Center(child: CircularProgressIndicator()),
              error: (e, _) => Center(
                child: Column(
                  mainAxisAlignment: MainAxisAlignment.center,
                  children: [
                    const Icon(Icons.cloud_off, size: 48, color: Colors.grey),
                    const SizedBox(height: 16),
                    const Text('Follow-ups konnten nicht geladen werden'),
                    const SizedBox(height: 8),
                    FilledButton(
                      onPressed: () => ref.invalidate(followUpProvider),
                      child: const Text('Erneut versuchen'),
                    ),
                  ],
                ),
              ),
              data: (items) => _buildList(items),
            ),
          ),
        ],
      ),
      floatingActionButton: FloatingActionButton(
        onPressed: () => _showCreateDialog(),
        child: const Icon(Icons.add),
      ),
    );
  }

  Widget _buildFilterChips() {
    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
      child: Wrap(
        spacing: 8,
        children: [
          _chip('Offen', 'open'),
          _chip('Erledigt', 'done'),
          _chip('Abgebrochen', 'cancelled'),
          _chip('Alle', 'all'),
        ],
      ),
    );
  }

  Widget _chip(String label, String value) {
    return FilterChip(
      label: Text(label),
      selected: _filter == value,
      onSelected: (_) => setState(() => _filter = value),
    );
  }

  IconData _typeIcon(String type) => switch (type) {
        'reminder' => Icons.alarm,
        'check_in' => Icons.fact_check,
        'deadline' => Icons.event_busy,
        _ => Icons.bookmark,
      };

  Widget _buildList(List<FollowUp> items) {
    final filtered = items.where((f) {
      if (_filter == 'all') return true;
      return f.status == _filter;
    }).toList();

    if (filtered.isEmpty) {
      return Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            const Icon(Icons.fact_check_outlined, size: 48, color: Colors.grey),
            const SizedBox(height: 16),
            Text(
              _filter == 'all'
                  ? 'Keine Follow-ups vorhanden'
                  : 'Keine ${_filter == 'open' ? 'offenen' : _filter == 'done' ? 'erledigten' : 'abgebrochenen'} Follow-ups',
              style: const TextStyle(color: Colors.grey),
            ),
          ],
        ),
      );
    }

    return RefreshIndicator(
      onRefresh: () async => ref.read(followUpProvider.notifier).refresh(),
      child: ListView.builder(
        padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 4),
        itemCount: filtered.length,
        itemBuilder: (_, i) => _buildItem(filtered[i]),
      ),
    );
  }

  Widget _buildItem(FollowUp item) {
    final isOverdue = item.isOverdue;
    final dateFormat = DateFormat('dd.MM.yyyy');

    return Card(
      color: isOverdue ? Colors.red.shade900.withValues(alpha: 0.3) : null,
      child: ListTile(
        leading: Icon(
          _typeIcon(item.type),
          color: isOverdue ? Colors.red.shade300 : null,
        ),
        title: Text(
          item.title,
          style: TextStyle(
            decoration:
                item.status == 'done' ? TextDecoration.lineThrough : null,
          ),
        ),
        subtitle: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text('${item.typeLabel} \u2022 ${item.statusLabel}'),
            if (item.dueDate != null)
              Text(
                'Faellig: ${dateFormat.format(item.dueDate!)}',
                style: TextStyle(
                  color: isOverdue ? Colors.red.shade300 : Colors.grey,
                ),
              ),
          ],
        ),
        trailing: item.status == 'open'
            ? PopupMenuButton<String>(
                onSelected: (action) {
                  if (action == 'done') {
                    ref.read(followUpProvider.notifier).markDone(item.id);
                  } else if (action == 'cancel') {
                    ref.read(followUpProvider.notifier).cancel(item.id);
                  }
                },
                itemBuilder: (_) => [
                  const PopupMenuItem(
                    value: 'done',
                    child: Text('Erledigt'),
                  ),
                  const PopupMenuItem(
                    value: 'cancel',
                    child: Text('Abbrechen'),
                  ),
                ],
              )
            : null,
      ),
    );
  }

  Future<void> _showCreateDialog() async {
    final titleCtrl = TextEditingController();
    final notesCtrl = TextEditingController();
    final refCtrl = TextEditingController();
    String type = 'custom';
    DateTime? dueDate;

    await showDialog<void>(
      context: context,
      builder: (ctx) => StatefulBuilder(
        builder: (ctx, setDialogState) => AlertDialog(
          title: const Text('Neues Follow-up'),
          content: SingleChildScrollView(
            child: Column(
              mainAxisSize: MainAxisSize.min,
              children: [
                TextField(
                  controller: titleCtrl,
                  decoration: const InputDecoration(
                    labelText: 'Titel',
                    border: OutlineInputBorder(),
                  ),
                ),
                const SizedBox(height: 12),
                DropdownButtonFormField<String>(
                  value: type,
                  decoration: const InputDecoration(
                    labelText: 'Typ',
                    border: OutlineInputBorder(),
                  ),
                  items: const [
                    DropdownMenuItem(value: 'reminder', child: Text('Erinnerung')),
                    DropdownMenuItem(value: 'check_in', child: Text('Nachfrage')),
                    DropdownMenuItem(value: 'deadline', child: Text('Frist')),
                    DropdownMenuItem(value: 'custom', child: Text('Eigenes')),
                  ],
                  onChanged: (v) => setDialogState(() => type = v!),
                ),
                const SizedBox(height: 12),
                ListTile(
                  contentPadding: EdgeInsets.zero,
                  title: Text(
                    dueDate != null
                        ? 'Faellig: ${DateFormat('dd.MM.yyyy').format(dueDate!)}'
                        : 'Faelligkeitsdatum (optional)',
                  ),
                  trailing: const Icon(Icons.calendar_today),
                  onTap: () async {
                    final picked = await showDatePicker(
                      context: ctx,
                      initialDate: DateTime.now().add(const Duration(days: 1)),
                      firstDate: DateTime.now(),
                      lastDate: DateTime.now().add(const Duration(days: 365)),
                    );
                    if (picked != null) {
                      setDialogState(() => dueDate = picked);
                    }
                  },
                ),
                const SizedBox(height: 12),
                TextField(
                  controller: notesCtrl,
                  decoration: const InputDecoration(
                    labelText: 'Notizen (optional)',
                    border: OutlineInputBorder(),
                  ),
                  maxLines: 2,
                ),
                const SizedBox(height: 12),
                TextField(
                  controller: refCtrl,
                  decoration: const InputDecoration(
                    labelText: 'Referenz (optional)',
                    border: OutlineInputBorder(),
                  ),
                ),
              ],
            ),
          ),
          actions: [
            TextButton(
              onPressed: () => Navigator.pop(ctx),
              child: const Text('Abbrechen'),
            ),
            FilledButton(
              onPressed: () {
                final title = titleCtrl.text.trim();
                if (title.isEmpty) return;
                ref.read(followUpProvider.notifier).create(
                      title: title,
                      type: type,
                      dueDate: dueDate,
                      notes: notesCtrl.text.trim().isNotEmpty
                          ? notesCtrl.text.trim()
                          : null,
                      reference: refCtrl.text.trim().isNotEmpty
                          ? refCtrl.text.trim()
                          : null,
                    );
                Navigator.pop(ctx);
              },
              child: const Text('Erstellen'),
            ),
          ],
        ),
      ),
    );
  }
}
