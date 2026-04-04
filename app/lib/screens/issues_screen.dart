import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../services/github_service.dart';
import '../providers/auth_provider.dart';

final githubServiceProvider = Provider<GitHubService>((ref) {
  return GitHubService(ref.watch(apiServiceProvider));
});

final _issuesProvider = FutureProvider.autoDispose<List<Map<String, dynamic>>>((ref) async {
  return ref.read(githubServiceProvider).getIssues();
});

final _labelsProvider = FutureProvider.autoDispose<List<Map<String, dynamic>>>((ref) async {
  return ref.read(githubServiceProvider).getLabels();
});

class IssuesScreen extends ConsumerStatefulWidget {
  const IssuesScreen({super.key});
  @override
  ConsumerState<IssuesScreen> createState() => _IssuesScreenState();
}

class _IssuesScreenState extends ConsumerState<IssuesScreen> {
  String? _labelFilter;
  String _stateFilter = 'open';

  @override
  Widget build(BuildContext context) {
    final issuesState = ref.watch(_issuesProvider);
    final labelsState = ref.watch(_labelsProvider);
    final colorScheme = Theme.of(context).colorScheme;

    return Scaffold(
      appBar: AppBar(
        title: const Text('Issues'),
        actions: [
          PopupMenuButton<String>(
            icon: const Icon(Icons.filter_list),
            tooltip: 'Status',
            onSelected: (v) => setState(() => _stateFilter = v),
            itemBuilder: (_) => [
              PopupMenuItem(value: 'open', child: Text('Offen${_stateFilter == 'open' ? ' \u2713' : ''}')),
              PopupMenuItem(value: 'closed', child: Text('Geschlossen${_stateFilter == 'closed' ? ' \u2713' : ''}')),
              PopupMenuItem(value: 'all', child: Text('Alle${_stateFilter == 'all' ? ' \u2713' : ''}')),
            ],
          ),
          IconButton(
            icon: const Icon(Icons.refresh),
            tooltip: 'Aktualisieren',
            onPressed: () {
              ref.invalidate(_issuesProvider);
              ref.invalidate(_labelsProvider);
            },
          ),
        ],
      ),
      body: Column(
        children: [
          // Label filter chips
          labelsState.when(
            loading: () => const SizedBox(height: 48),
            error: (_, __) => const SizedBox(height: 48),
            data: (labels) => SizedBox(
              height: 48,
              child: ListView(
                scrollDirection: Axis.horizontal,
                padding: const EdgeInsets.symmetric(horizontal: 12),
                children: [
                  Padding(
                    padding: const EdgeInsets.only(right: 8),
                    child: FilterChip(
                      label: const Text('Alle'),
                      selected: _labelFilter == null,
                      onSelected: (_) => setState(() => _labelFilter = null),
                    ),
                  ),
                  ...labels.map((l) {
                    final name = l['name'] as String? ?? '';
                    final selected = _labelFilter == name;
                    final colorStr = l['color'] as String?;
                    Color? chipColor;
                    if (colorStr != null && colorStr.isNotEmpty) {
                      try {
                        chipColor = Color(int.parse('FF$colorStr', radix: 16));
                      } catch (_) {}
                    }
                    return Padding(
                      padding: const EdgeInsets.only(right: 8),
                      child: FilterChip(
                        label: Text(name),
                        selected: selected,
                        backgroundColor: chipColor?.withOpacity(0.3),
                        onSelected: (_) => setState(() => _labelFilter = selected ? null : name),
                      ),
                    );
                  }),
                ],
              ),
            ),
          ),
          Expanded(
            child: issuesState.when(
              loading: () => const Center(child: CircularProgressIndicator()),
              error: (e, _) => Center(
                child: Column(
                  mainAxisAlignment: MainAxisAlignment.center,
                  children: [
                    const Icon(Icons.cloud_off, size: 48, color: Colors.grey),
                    const SizedBox(height: 16),
                    const Text('Issues konnten nicht geladen werden'),
                    const SizedBox(height: 8),
                    FilledButton(
                      onPressed: () => ref.invalidate(_issuesProvider),
                      child: const Text('Erneut versuchen'),
                    ),
                  ],
                ),
              ),
              data: (issues) {
                final filtered = issues.where((issue) {
                  final state = issue['state'] as String? ?? 'open';
                  if (_stateFilter != 'all' && state != _stateFilter) return false;
                  if (_labelFilter != null) {
                    final labels = (issue['labels'] as List?)
                        ?.map((l) => l is Map ? l['name'] as String? ?? '' : l.toString())
                        .toList() ?? [];
                    if (!labels.contains(_labelFilter)) return false;
                  }
                  return true;
                }).toList();

                if (filtered.isEmpty) {
                  return const Center(
                    child: Column(
                      mainAxisAlignment: MainAxisAlignment.center,
                      children: [
                        Icon(Icons.bug_report_outlined, size: 48, color: Colors.grey),
                        SizedBox(height: 16),
                        Text('Keine Issues', style: TextStyle(color: Colors.grey)),
                      ],
                    ),
                  );
                }

                return RefreshIndicator(
                  onRefresh: () async {
                    ref.invalidate(_issuesProvider);
                    ref.invalidate(_labelsProvider);
                  },
                  child: ListView.builder(
                    padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 4),
                    itemCount: filtered.length,
                    itemBuilder: (_, i) => _IssueCard(
                      issue: filtered[i],
                      colorScheme: colorScheme,
                    ),
                  ),
                );
              },
            ),
          ),
        ],
      ),
      floatingActionButton: FloatingActionButton(
        onPressed: () => _showCreateDialog(context),
        child: const Icon(Icons.add),
      ),
    );
  }

  Future<void> _showCreateDialog(BuildContext context) async {
    final titleController = TextEditingController();
    final bodyController = TextEditingController();
    final selectedLabels = <String>{};
    final labels = ref.read(_labelsProvider).valueOrNull ?? [];

    final ok = await showDialog<bool>(
      context: context,
      builder: (ctx) => StatefulBuilder(
        builder: (ctx, setDialogState) => AlertDialog(
          title: const Text('Neues Issue'),
          content: SingleChildScrollView(
            child: Column(
              mainAxisSize: MainAxisSize.min,
              children: [
                TextField(
                  controller: titleController,
                  decoration: const InputDecoration(
                    labelText: 'Titel',
                    border: OutlineInputBorder(),
                  ),
                ),
                const SizedBox(height: 12),
                TextField(
                  controller: bodyController,
                  maxLines: 4,
                  decoration: const InputDecoration(
                    labelText: 'Beschreibung',
                    border: OutlineInputBorder(),
                  ),
                ),
                if (labels.isNotEmpty) ...[
                  const SizedBox(height: 12),
                  Wrap(
                    spacing: 6,
                    children: labels.map((l) {
                      final name = l['name'] as String? ?? '';
                      return FilterChip(
                        label: Text(name),
                        selected: selectedLabels.contains(name),
                        onSelected: (v) => setDialogState(() {
                          if (v) {
                            selectedLabels.add(name);
                          } else {
                            selectedLabels.remove(name);
                          }
                        }),
                      );
                    }).toList(),
                  ),
                ],
              ],
            ),
          ),
          actions: [
            TextButton(onPressed: () => Navigator.pop(ctx, false), child: const Text('Abbrechen')),
            FilledButton(onPressed: () => Navigator.pop(ctx, true), child: const Text('Erstellen')),
          ],
        ),
      ),
    );

    if (ok == true && titleController.text.trim().isNotEmpty) {
      await ref.read(githubServiceProvider).createIssue(
        title: titleController.text.trim(),
        body: bodyController.text.trim().isNotEmpty ? bodyController.text.trim() : null,
        labels: selectedLabels.isNotEmpty ? selectedLabels.toList() : null,
      );
      ref.invalidate(_issuesProvider);
    }

    titleController.dispose();
    bodyController.dispose();
  }
}

class _IssueCard extends StatelessWidget {
  final Map<String, dynamic> issue;
  final ColorScheme colorScheme;

  const _IssueCard({required this.issue, required this.colorScheme});

  @override
  Widget build(BuildContext context) {
    final title = issue['title'] as String? ?? '';
    final number = issue['number'] as int?;
    final state = issue['state'] as String? ?? 'open';
    final labels = (issue['labels'] as List?) ?? [];
    final createdAt = issue['created_at'] as String?;

    return Card(
      margin: const EdgeInsets.symmetric(vertical: 4),
      child: Padding(
        padding: const EdgeInsets.all(12),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Icon(
                  state == 'open' ? Icons.radio_button_unchecked : Icons.check_circle,
                  size: 18,
                  color: state == 'open' ? Colors.green : Colors.purple,
                ),
                const SizedBox(width: 8),
                if (number != null)
                  Text('#$number ', style: const TextStyle(color: Colors.grey, fontSize: 13)),
                Expanded(
                  child: Text(title, style: const TextStyle(fontWeight: FontWeight.bold)),
                ),
              ],
            ),
            if (labels.isNotEmpty) ...[
              const SizedBox(height: 8),
              Wrap(
                spacing: 4,
                runSpacing: 4,
                children: labels.map((l) {
                  final name = l is Map ? l['name'] as String? ?? '' : l.toString();
                  final colorStr = l is Map ? l['color'] as String? : null;
                  Color? chipColor;
                  if (colorStr != null && colorStr.isNotEmpty) {
                    try {
                      chipColor = Color(int.parse('FF$colorStr', radix: 16));
                    } catch (_) {}
                  }
                  return Container(
                    padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
                    decoration: BoxDecoration(
                      color: chipColor?.withOpacity(0.3) ?? colorScheme.surfaceContainerHighest,
                      borderRadius: BorderRadius.circular(4),
                    ),
                    child: Text(name, style: const TextStyle(fontSize: 11)),
                  );
                }).toList(),
              ),
            ],
            if (createdAt != null) ...[
              const SizedBox(height: 4),
              Text(
                _formatDate(createdAt),
                style: const TextStyle(fontSize: 11, color: Colors.grey),
              ),
            ],
          ],
        ),
      ),
    );
  }

  String _formatDate(String iso) {
    try {
      final dt = DateTime.parse(iso);
      return '${dt.day.toString().padLeft(2, '0')}.${dt.month.toString().padLeft(2, '0')}.${dt.year}';
    } catch (_) {
      return iso;
    }
  }
}
