import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../providers/task_provider.dart';
import '../models/task.dart';
import '../widgets/task_card.dart';

class TasksScreen extends ConsumerStatefulWidget {
  const TasksScreen({super.key});
  @override
  ConsumerState<TasksScreen> createState() => _TasksScreenState();
}

class _TasksScreenState extends ConsumerState<TasksScreen> {
  final _addController = TextEditingController();
  String _filter = 'open'; // 'open', 'done', 'all'
  String _newPriority = 'medium';

  @override
  void dispose() {
    _addController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final state = ref.watch(taskProvider);

    return Scaffold(
      appBar: AppBar(
        title: const Text('Aufgaben'),
        actions: [
          PopupMenuButton<String>(
            icon: const Icon(Icons.filter_list),
            tooltip: 'Filter',
            onSelected: (v) => setState(() => _filter = v),
            itemBuilder: (_) => [
              PopupMenuItem(value: 'open', child: Text('Offen${_filter == 'open' ? ' \u2713' : ''}')),
              PopupMenuItem(value: 'done', child: Text('Erledigt${_filter == 'done' ? ' \u2713' : ''}')),
              PopupMenuItem(value: 'all', child: Text('Alle${_filter == 'all' ? ' \u2713' : ''}')),
            ],
          ),
          IconButton(
            icon: const Icon(Icons.refresh),
            tooltip: 'Aktualisieren',
            onPressed: () => ref.read(taskProvider.notifier).refresh(),
          ),
        ],
      ),
      body: Column(
        children: [
          _buildAddField(),
          Expanded(child: state.when(
            loading: () => const Center(child: CircularProgressIndicator()),
            error: (e, _) => Center(child: Column(
              mainAxisAlignment: MainAxisAlignment.center,
              children: [
                const Icon(Icons.cloud_off, size: 48, color: Colors.grey),
                const SizedBox(height: 16),
                const Text('Aufgaben konnten nicht geladen werden'),
                const SizedBox(height: 8),
                FilledButton(
                  onPressed: () => ref.invalidate(taskProvider),
                  child: const Text('Erneut versuchen'),
                ),
              ],
            )),
            data: (tasks) => _buildList(tasks),
          )),
        ],
      ),
    );
  }

  Widget _buildAddField() {
    return Padding(
      padding: const EdgeInsets.fromLTRB(16, 8, 16, 4),
      child: Row(
        children: [
          Expanded(
            child: TextField(
              controller: _addController,
              decoration: const InputDecoration(
                hintText: 'Neue Aufgabe...',
                border: OutlineInputBorder(),
                isDense: true,
                contentPadding: EdgeInsets.symmetric(horizontal: 12, vertical: 10),
              ),
              onSubmitted: (_) => _addTask(),
            ),
          ),
          const SizedBox(width: 8),
          PopupMenuButton<String>(
            tooltip: 'Prioritaet',
            onSelected: (v) => setState(() => _newPriority = v),
            child: Container(
              padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 8),
              decoration: BoxDecoration(
                border: Border.all(color: Colors.grey.shade600),
                borderRadius: BorderRadius.circular(4),
              ),
              child: Row(
                mainAxisSize: MainAxisSize.min,
                children: [
                  Container(
                    width: 10,
                    height: 10,
                    decoration: BoxDecoration(
                      color: switch (_newPriority) {
                        'high' => Colors.red.shade400,
                        'low' => Colors.green.shade400,
                        _ => Colors.orange.shade400,
                      },
                      shape: BoxShape.circle,
                    ),
                  ),
                  const SizedBox(width: 4),
                  const Icon(Icons.arrow_drop_down, size: 18),
                ],
              ),
            ),
            itemBuilder: (_) => [
              const PopupMenuItem(value: 'high', child: Text('\ud83d\udd34 Hoch')),
              const PopupMenuItem(value: 'medium', child: Text('\ud83d\udfe1 Mittel')),
              const PopupMenuItem(value: 'low', child: Text('\ud83d\udfe2 Niedrig')),
            ],
          ),
          const SizedBox(width: 8),
          FilledButton(onPressed: _addTask, child: const Icon(Icons.add)),
        ],
      ),
    );
  }

  Future<void> _addTask() async {
    final title = _addController.text.trim();
    if (title.isEmpty) return;
    _addController.clear();
    await ref.read(taskProvider.notifier).addTask(title, priority: _newPriority);
  }

  Widget _buildList(List<Task> tasks) {
    final filtered = tasks.where((t) {
      if (_filter == 'open') return !t.isDone;
      if (_filter == 'done') return t.isDone;
      return true;
    }).toList();

    if (filtered.isEmpty) {
      return Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            const Icon(Icons.check_box_outlined, size: 48, color: Colors.grey),
            const SizedBox(height: 16),
            Text(
              _filter == 'done' ? 'Keine erledigten Aufgaben' : 'Keine offenen Aufgaben',
              style: const TextStyle(color: Colors.grey),
            ),
          ],
        ),
      );
    }

    return RefreshIndicator(
      onRefresh: () async => ref.read(taskProvider.notifier).refresh(),
      child: ListView.builder(
        padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 4),
        itemCount: filtered.length,
        itemBuilder: (_, i) => TaskCard(
          task: filtered[i],
          onComplete: () => ref.read(taskProvider.notifier).completeTask(filtered[i].id),
          onDelete: () async {
            final ok = await showDialog<bool>(
              context: context,
              builder: (_) => AlertDialog(
                title: const Text('Aufgabe loeschen?'),
                content: Text(filtered[i].title),
                actions: [
                  TextButton(onPressed: () => Navigator.pop(context, false), child: const Text('Abbrechen')),
                  FilledButton(onPressed: () => Navigator.pop(context, true), child: const Text('Loeschen')),
                ],
              ),
            );
            if (ok == true) ref.read(taskProvider.notifier).deleteTask(filtered[i].id);
          },
        ),
      ),
    );
  }
}
