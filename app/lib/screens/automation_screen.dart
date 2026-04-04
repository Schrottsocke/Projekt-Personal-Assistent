import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../providers/automation_provider.dart';
import '../models/automation_rule.dart';

class AutomationScreen extends ConsumerStatefulWidget {
  const AutomationScreen({super.key});
  @override
  ConsumerState<AutomationScreen> createState() => _AutomationScreenState();
}

class _AutomationScreenState extends ConsumerState<AutomationScreen> {
  @override
  Widget build(BuildContext context) {
    final state = ref.watch(automationProvider);
    final colorScheme = Theme.of(context).colorScheme;

    return Scaffold(
      appBar: AppBar(
        title: const Text('Automation'),
        actions: [
          IconButton(
            icon: const Icon(Icons.refresh),
            tooltip: 'Aktualisieren',
            onPressed: () => ref.read(automationProvider.notifier).refresh(),
          ),
        ],
      ),
      body: state.when(
        loading: () => const Center(child: CircularProgressIndicator()),
        error: (e, _) => Center(
          child: Column(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              const Icon(Icons.cloud_off, size: 48, color: Colors.grey),
              const SizedBox(height: 16),
              const Text('Regeln konnten nicht geladen werden'),
              const SizedBox(height: 8),
              FilledButton(
                onPressed: () => ref.invalidate(automationProvider),
                child: const Text('Erneut versuchen'),
              ),
            ],
          ),
        ),
        data: (rules) {
          if (rules.isEmpty) {
            return const Center(
              child: Column(
                mainAxisAlignment: MainAxisAlignment.center,
                children: [
                  Icon(Icons.auto_fix_high_outlined, size: 48, color: Colors.grey),
                  SizedBox(height: 16),
                  Text('Keine Automation-Regeln', style: TextStyle(color: Colors.grey)),
                ],
              ),
            );
          }

          return RefreshIndicator(
            onRefresh: () async => ref.read(automationProvider.notifier).refresh(),
            child: ListView.builder(
              padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 4),
              itemCount: rules.length,
              itemBuilder: (_, i) => _RuleCard(
                rule: rules[i],
                colorScheme: colorScheme,
                onToggle: () => ref.read(automationProvider.notifier).toggle(rules[i].id),
                onTest: () async {
                  await ref.read(automationProvider.notifier).evaluate(rules[i].id);
                  if (context.mounted) {
                    ScaffoldMessenger.of(context).showSnackBar(
                      SnackBar(content: Text('Regel "${rules[i].name}" getestet')),
                    );
                  }
                },
                onDelete: () async {
                  final ok = await showDialog<bool>(
                    context: context,
                    builder: (_) => AlertDialog(
                      title: const Text('Regel loeschen?'),
                      content: Text(rules[i].name),
                      actions: [
                        TextButton(onPressed: () => Navigator.pop(context, false), child: const Text('Abbrechen')),
                        FilledButton(onPressed: () => Navigator.pop(context, true), child: const Text('Loeschen')),
                      ],
                    ),
                  );
                  if (ok == true) {
                    await ref.read(automationProvider.notifier).delete(rules[i].id);
                  }
                },
              ),
            ),
          );
        },
      ),
      floatingActionButton: FloatingActionButton(
        onPressed: () => _showCreateDialog(context),
        child: const Icon(Icons.add),
      ),
    );
  }

  Future<void> _showCreateDialog(BuildContext context) async {
    final nameController = TextEditingController();
    final descController = TextEditingController();
    final triggerController = TextEditingController();
    final actionController = TextEditingController();

    final ok = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text('Neue Regel'),
        content: SingleChildScrollView(
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              TextField(
                controller: nameController,
                decoration: const InputDecoration(
                  labelText: 'Name',
                  border: OutlineInputBorder(),
                ),
              ),
              const SizedBox(height: 12),
              TextField(
                controller: descController,
                decoration: const InputDecoration(
                  labelText: 'Beschreibung',
                  border: OutlineInputBorder(),
                ),
              ),
              const SizedBox(height: 12),
              TextField(
                controller: triggerController,
                decoration: const InputDecoration(
                  labelText: 'Trigger (z.B. time:08:00)',
                  border: OutlineInputBorder(),
                ),
              ),
              const SizedBox(height: 12),
              TextField(
                controller: actionController,
                decoration: const InputDecoration(
                  labelText: 'Aktion (z.B. notify:Einkaufen)',
                  border: OutlineInputBorder(),
                ),
              ),
            ],
          ),
        ),
        actions: [
          TextButton(onPressed: () => Navigator.pop(ctx, false), child: const Text('Abbrechen')),
          FilledButton(onPressed: () => Navigator.pop(ctx, true), child: const Text('Erstellen')),
        ],
      ),
    );

    if (ok == true && nameController.text.trim().isNotEmpty) {
      await ref.read(automationProvider.notifier).create(
        name: nameController.text.trim(),
        description: descController.text.trim().isNotEmpty ? descController.text.trim() : null,
        trigger: {'type': triggerController.text.trim()},
        action: {'type': actionController.text.trim()},
      );
    }

    nameController.dispose();
    descController.dispose();
    triggerController.dispose();
    actionController.dispose();
  }
}

class _RuleCard extends StatelessWidget {
  final AutomationRule rule;
  final ColorScheme colorScheme;
  final VoidCallback onToggle;
  final VoidCallback onTest;
  final VoidCallback onDelete;

  const _RuleCard({
    required this.rule,
    required this.colorScheme,
    required this.onToggle,
    required this.onTest,
    required this.onDelete,
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
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(rule.name, style: const TextStyle(fontWeight: FontWeight.bold)),
                      if (rule.description != null)
                        Padding(
                          padding: const EdgeInsets.only(top: 4),
                          child: Text(rule.description!, style: const TextStyle(color: Colors.grey, fontSize: 13)),
                        ),
                    ],
                  ),
                ),
                Switch(
                  value: rule.active,
                  onChanged: (_) => onToggle(),
                ),
              ],
            ),
            const SizedBox(height: 8),
            Row(
              children: [
                Text('Ausloesungen: ${rule.triggerCount}', style: const TextStyle(fontSize: 12, color: Colors.grey)),
                if (rule.lastTriggered != null) ...[
                  const SizedBox(width: 12),
                  Text(
                    'Zuletzt: ${_formatDate(rule.lastTriggered!)}',
                    style: const TextStyle(fontSize: 12, color: Colors.grey),
                  ),
                ],
                const Spacer(),
                IconButton(
                  icon: const Icon(Icons.play_circle_outline, size: 20),
                  tooltip: 'Testen',
                  onPressed: onTest,
                ),
                IconButton(
                  icon: const Icon(Icons.delete_outline, size: 20),
                  tooltip: 'Loeschen',
                  onPressed: onDelete,
                ),
              ],
            ),
          ],
        ),
      ),
    );
  }

  String _formatDate(DateTime dt) {
    return '${dt.day.toString().padLeft(2, '0')}.${dt.month.toString().padLeft(2, '0')}. ${dt.hour.toString().padLeft(2, '0')}:${dt.minute.toString().padLeft(2, '0')}';
  }
}
