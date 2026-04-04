import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../providers/template_provider.dart';
import '../models/template.dart';

class TemplatesScreen extends ConsumerStatefulWidget {
  const TemplatesScreen({super.key});
  @override
  ConsumerState<TemplatesScreen> createState() => _TemplatesScreenState();
}

class _TemplatesScreenState extends ConsumerState<TemplatesScreen> {
  String? _selectedCategory;

  static const _categories = [
    (null, 'Alle'),
    ('shopping', 'Einkaufsliste'),
    ('task', 'Aufgabe'),
    ('checklist', 'Checkliste'),
    ('routine', 'Routine'),
    ('mealplan', 'Wochenplan'),
    ('message', 'Nachricht'),
  ];

  @override
  Widget build(BuildContext context) {
    final state = ref.watch(templateProvider);
    final colorScheme = Theme.of(context).colorScheme;

    return Scaffold(
      appBar: AppBar(
        title: const Text('Vorlagen'),
        actions: [
          IconButton(
            icon: const Icon(Icons.refresh),
            tooltip: 'Aktualisieren',
            onPressed: () => ref.read(templateProvider.notifier).refresh(category: _selectedCategory),
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
              children: _categories.map((c) {
                final selected = _selectedCategory == c.$1;
                return Padding(
                  padding: const EdgeInsets.only(right: 8),
                  child: FilterChip(
                    label: Text(c.$2),
                    selected: selected,
                    onSelected: (_) {
                      setState(() => _selectedCategory = selected ? null : c.$1);
                      ref.read(templateProvider.notifier).refresh(category: _selectedCategory);
                    },
                  ),
                );
              }).toList(),
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
                    const Text('Vorlagen konnten nicht geladen werden'),
                    const SizedBox(height: 8),
                    FilledButton(
                      onPressed: () => ref.invalidate(templateProvider),
                      child: const Text('Erneut versuchen'),
                    ),
                  ],
                ),
              ),
              data: (templates) {
                final filtered = _selectedCategory == null
                    ? templates
                    : templates.where((t) => t.category == _selectedCategory).toList();

                if (filtered.isEmpty) {
                  return const Center(
                    child: Column(
                      mainAxisAlignment: MainAxisAlignment.center,
                      children: [
                        Icon(Icons.copy_outlined, size: 48, color: Colors.grey),
                        SizedBox(height: 16),
                        Text('Keine Vorlagen vorhanden', style: TextStyle(color: Colors.grey)),
                      ],
                    ),
                  );
                }

                return RefreshIndicator(
                  onRefresh: () async => ref.read(templateProvider.notifier).refresh(category: _selectedCategory),
                  child: ListView.builder(
                    padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 4),
                    itemCount: filtered.length,
                    itemBuilder: (_, i) => _TemplateCard(
                      template: filtered[i],
                      colorScheme: colorScheme,
                      onApply: () async {
                        await ref.read(templateProvider.notifier).apply(filtered[i].id);
                        if (context.mounted) {
                          ScaffoldMessenger.of(context).showSnackBar(
                            SnackBar(content: Text('Vorlage "${filtered[i].name}" angewendet')),
                          );
                        }
                      },
                      onDelete: () async {
                        final ok = await showDialog<bool>(
                          context: context,
                          builder: (_) => AlertDialog(
                            title: const Text('Vorlage loeschen?'),
                            content: Text(filtered[i].name),
                            actions: [
                              TextButton(onPressed: () => Navigator.pop(context, false), child: const Text('Abbrechen')),
                              FilledButton(onPressed: () => Navigator.pop(context, true), child: const Text('Loeschen')),
                            ],
                          ),
                        );
                        if (ok == true) {
                          await ref.read(templateProvider.notifier).delete(filtered[i].id);
                        }
                      },
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
    final nameController = TextEditingController();
    final contentController = TextEditingController();
    String category = 'task';

    final ok = await showDialog<bool>(
      context: context,
      builder: (ctx) => StatefulBuilder(
        builder: (ctx, setDialogState) => AlertDialog(
          title: const Text('Neue Vorlage'),
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
                DropdownButtonFormField<String>(
                  value: category,
                  decoration: const InputDecoration(
                    labelText: 'Kategorie',
                    border: OutlineInputBorder(),
                  ),
                  items: _categories.where((c) => c.$1 != null).map((c) {
                    return DropdownMenuItem(value: c.$1, child: Text(c.$2));
                  }).toList(),
                  onChanged: (v) => setDialogState(() => category = v ?? 'task'),
                ),
                const SizedBox(height: 12),
                TextField(
                  controller: contentController,
                  maxLines: 4,
                  decoration: const InputDecoration(
                    labelText: 'Inhalt',
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
      ),
    );

    if (ok == true && nameController.text.trim().isNotEmpty) {
      await ref.read(templateProvider.notifier).create(
        name: nameController.text.trim(),
        category: category,
        content: contentController.text.trim().isNotEmpty
            ? {'text': contentController.text.trim()}
            : {},
      );
    }

    nameController.dispose();
    contentController.dispose();
  }
}

class _TemplateCard extends StatelessWidget {
  final Template template;
  final ColorScheme colorScheme;
  final VoidCallback onApply;
  final VoidCallback onDelete;

  const _TemplateCard({
    required this.template,
    required this.colorScheme,
    required this.onApply,
    required this.onDelete,
  });

  @override
  Widget build(BuildContext context) {
    return Card(
      margin: const EdgeInsets.symmetric(vertical: 4),
      child: ListTile(
        title: Text(template.name),
        subtitle: Text(template.categoryLabel),
        leading: Container(
          padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
          decoration: BoxDecoration(
            color: colorScheme.primaryContainer,
            borderRadius: BorderRadius.circular(4),
          ),
          child: Text(
            template.categoryLabel,
            style: TextStyle(fontSize: 11, color: colorScheme.onPrimaryContainer),
          ),
        ),
        trailing: Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            IconButton(
              icon: const Icon(Icons.play_arrow),
              tooltip: 'Anwenden',
              onPressed: onApply,
            ),
            IconButton(
              icon: const Icon(Icons.delete_outline),
              tooltip: 'Loeschen',
              onPressed: onDelete,
            ),
          ],
        ),
      ),
    );
  }
}
