import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../models/meal_plan_entry.dart';
import '../providers/mealplan_provider.dart';

class MealPlanScreen extends ConsumerStatefulWidget {
  const MealPlanScreen({super.key});

  @override
  ConsumerState<MealPlanScreen> createState() => _MealPlanScreenState();
}

class _MealPlanScreenState extends ConsumerState<MealPlanScreen> {
  static const _mealTypes = ['breakfast', 'lunch', 'dinner'];
  static const _mealLabels = {'breakfast': 'Frühstück', 'lunch': 'Mittagessen', 'dinner': 'Abendessen'};
  static const _dayLabels = ['Mo', 'Di', 'Mi', 'Do', 'Fr', 'Sa', 'So'];

  @override
  Widget build(BuildContext context) {
    final state = ref.watch(mealplanProvider);
    final notifier = ref.read(mealplanProvider.notifier);
    final weekStart = notifier.weekStart;
    final monday = DateTime.parse(weekStart);
    final kwNumber = _weekNumber(monday);

    return Scaffold(
      appBar: AppBar(
        title: const Text('Wochenplan'),
        actions: [
          IconButton(
            icon: const Icon(Icons.shopping_cart),
            tooltip: 'Woche zur Einkaufsliste',
            onPressed: () async {
              await notifier.exportToShopping();
              if (context.mounted) {
                ScaffoldMessenger.of(context).showSnackBar(
                  const SnackBar(content: Text('Zutaten zur Einkaufsliste hinzugefügt')),
                );
              }
            },
          ),
        ],
      ),
      body: Column(
        children: [
          // Week navigation
          Padding(
            padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
            child: Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                IconButton(
                  icon: const Icon(Icons.chevron_left),
                  onPressed: () => notifier.previousWeek(),
                ),
                Text(
                  'KW $kwNumber  (${_formatDate(monday)} – ${_formatDate(monday.add(const Duration(days: 6)))})',
                  style: Theme.of(context).textTheme.titleSmall,
                ),
                IconButton(
                  icon: const Icon(Icons.chevron_right),
                  onPressed: () => notifier.nextWeek(),
                ),
              ],
            ),
          ),
          const Divider(height: 1),
          // Grid
          Expanded(
            child: state.when(
              loading: () => const Center(child: CircularProgressIndicator()),
              error: (e, _) => Center(child: Text('Fehler: $e')),
              data: (entries) => _buildGrid(context, entries, monday),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildGrid(BuildContext context, List<MealPlanEntry> entries, DateTime monday) {
    return SingleChildScrollView(
      child: Table(
        border: TableBorder.all(color: Theme.of(context).dividerColor.withValues(alpha: 0.3)),
        columnWidths: const {0: FixedColumnWidth(80)},
        children: [
          // Header row
          TableRow(
            children: [
              const SizedBox(height: 36),
              ...List.generate(7, (i) {
                final day = monday.add(Duration(days: i));
                final isToday = _isToday(day);
                return Container(
                  height: 36,
                  alignment: Alignment.center,
                  color: isToday ? Theme.of(context).colorScheme.primaryContainer.withValues(alpha: 0.3) : null,
                  child: Text(
                    '${_dayLabels[i]} ${day.day}.',
                    style: TextStyle(
                      fontWeight: isToday ? FontWeight.bold : FontWeight.normal,
                      fontSize: 12,
                    ),
                  ),
                );
              }),
            ],
          ),
          // One row per meal type
          ..._mealTypes.map((mealType) {
            return TableRow(
              children: [
                Container(
                  height: 80,
                  alignment: Alignment.center,
                  padding: const EdgeInsets.all(4),
                  child: Text(
                    _mealLabels[mealType]!,
                    style: const TextStyle(fontSize: 11, fontWeight: FontWeight.w500),
                    textAlign: TextAlign.center,
                  ),
                ),
                ...List.generate(7, (dayIndex) {
                  final dayStr = _dateStr(monday.add(Duration(days: dayIndex)));
                  final cellEntries = entries.where((e) => e.plannedDate == dayStr && e.mealType == mealType).toList();
                  return _buildCell(context, cellEntries, dayStr, mealType);
                }),
              ],
            );
          }),
        ],
      ),
    );
  }

  Widget _buildCell(BuildContext context, List<MealPlanEntry> entries, String date, String mealType) {
    return SizedBox(
      height: 80,
      child: InkWell(
        onTap: entries.isEmpty ? () => _showAddDialog(context, date, mealType) : null,
        child: Padding(
          padding: const EdgeInsets.all(2),
          child: entries.isEmpty
              ? const Center(child: Icon(Icons.add, size: 16, color: Colors.grey))
              : Column(
                  mainAxisAlignment: MainAxisAlignment.center,
                  children: entries.map((e) => _entryChip(context, e)).toList(),
                ),
        ),
      ),
    );
  }

  Widget _entryChip(BuildContext context, MealPlanEntry entry) {
    return GestureDetector(
      onLongPress: () async {
        final confirm = await showDialog<bool>(
          context: context,
          builder: (_) => AlertDialog(
            title: const Text('Eintrag löschen?'),
            content: Text(entry.recipeTitle),
            actions: [
              TextButton(onPressed: () => Navigator.pop(context, false), child: const Text('Abbrechen')),
              FilledButton(onPressed: () => Navigator.pop(context, true), child: const Text('Löschen')),
            ],
          ),
        );
        if (confirm == true) {
          await ref.read(mealplanProvider.notifier).deleteEntry(entry.id);
        }
      },
      child: Container(
        margin: const EdgeInsets.only(bottom: 2),
        padding: const EdgeInsets.symmetric(horizontal: 4, vertical: 2),
        decoration: BoxDecoration(
          color: Theme.of(context).colorScheme.primaryContainer.withValues(alpha: 0.5),
          borderRadius: BorderRadius.circular(4),
        ),
        child: Text(
          entry.recipeTitle,
          style: const TextStyle(fontSize: 10),
          maxLines: 2,
          overflow: TextOverflow.ellipsis,
        ),
      ),
    );
  }

  Future<void> _showAddDialog(BuildContext context, String date, String mealType) async {
    final titleCtrl = TextEditingController();
    final notesCtrl = TextEditingController();
    int servings = 4;
    String selectedMealType = mealType;

    await showDialog(
      context: context,
      builder: (ctx) => StatefulBuilder(
        builder: (ctx, setDialogState) => AlertDialog(
          title: const Text('Mahlzeit hinzufügen'),
          content: SingleChildScrollView(
            child: Column(
              mainAxisSize: MainAxisSize.min,
              children: [
                Text('Datum: $date', style: Theme.of(context).textTheme.bodySmall),
                const SizedBox(height: 12),
                DropdownButtonFormField<String>(
                  value: selectedMealType,
                  decoration: const InputDecoration(labelText: 'Mahlzeit', border: OutlineInputBorder()),
                  items: _mealTypes.map((t) => DropdownMenuItem(value: t, child: Text(_mealLabels[t]!))).toList(),
                  onChanged: (v) => setDialogState(() => selectedMealType = v!),
                ),
                const SizedBox(height: 12),
                TextField(
                  controller: titleCtrl,
                  decoration: const InputDecoration(labelText: 'Rezeptname', border: OutlineInputBorder()),
                ),
                const SizedBox(height: 12),
                Row(
                  children: [
                    const Text('Portionen: '),
                    IconButton(
                      icon: const Icon(Icons.remove),
                      onPressed: servings > 1 ? () => setDialogState(() => servings--) : null,
                    ),
                    Text('$servings'),
                    IconButton(
                      icon: const Icon(Icons.add),
                      onPressed: () => setDialogState(() => servings++),
                    ),
                  ],
                ),
                const SizedBox(height: 12),
                TextField(
                  controller: notesCtrl,
                  decoration: const InputDecoration(labelText: 'Notizen', border: OutlineInputBorder()),
                  maxLines: 2,
                ),
              ],
            ),
          ),
          actions: [
            TextButton(onPressed: () => Navigator.pop(ctx), child: const Text('Abbrechen')),
            FilledButton(
              onPressed: () async {
                if (titleCtrl.text.trim().isEmpty) return;
                Navigator.pop(ctx);
                await ref.read(mealplanProvider.notifier).addEntry(
                  date: date,
                  mealType: selectedMealType,
                  recipeTitle: titleCtrl.text.trim(),
                  servings: servings,
                  notes: notesCtrl.text.trim().isEmpty ? null : notesCtrl.text.trim(),
                );
              },
              child: const Text('Hinzufügen'),
            ),
          ],
        ),
      ),
    );
  }

  String _dateStr(DateTime d) => '${d.year}-${d.month.toString().padLeft(2, '0')}-${d.day.toString().padLeft(2, '0')}';

  String _formatDate(DateTime d) => '${d.day}.${d.month}.';

  bool _isToday(DateTime d) {
    final now = DateTime.now();
    return d.year == now.year && d.month == now.month && d.day == now.day;
  }

  int _weekNumber(DateTime d) {
    final jan1 = DateTime(d.year, 1, 1);
    final dayOfYear = d.difference(jan1).inDays + 1;
    return ((dayOfYear - d.weekday + 10) / 7).floor();
  }
}
