import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../models/shift.dart';
import '../providers/shift_provider.dart';

class ShiftsScreen extends ConsumerStatefulWidget {
  const ShiftsScreen({super.key});
  @override
  ConsumerState<ShiftsScreen> createState() => _ShiftsScreenState();
}

class _ShiftsScreenState extends ConsumerState<ShiftsScreen> {
  late int _year;
  late int _month;

  @override
  void initState() {
    super.initState();
    final now = DateTime.now();
    _year = now.year;
    _month = now.month;
  }

  String get _monthKey => '$_year-${_month.toString().padLeft(2, '0')}';

  String get _monthLabel {
    const months = [
      '', 'Januar', 'Februar', 'Maerz', 'April', 'Mai', 'Juni',
      'Juli', 'August', 'September', 'Oktober', 'November', 'Dezember',
    ];
    return '${months[_month]} $_year';
  }

  void _prevMonth() {
    setState(() {
      _month--;
      if (_month < 1) { _month = 12; _year--; }
    });
    ref.read(shiftProvider.notifier).loadMonth(_monthKey);
  }

  void _nextMonth() {
    setState(() {
      _month++;
      if (_month > 12) { _month = 1; _year++; }
    });
    ref.read(shiftProvider.notifier).loadMonth(_monthKey);
  }

  Color _parseColor(String? hex) {
    if (hex == null || hex.isEmpty) return Colors.grey;
    final h = hex.startsWith('#') ? hex.substring(1) : hex;
    if (h.length == 6) return Color(int.parse('FF$h', radix: 16));
    if (h.length == 8) return Color(int.parse(h, radix: 16));
    return Colors.grey;
  }

  @override
  Widget build(BuildContext context) {
    final state = ref.watch(shiftProvider);
    final cs = Theme.of(context).colorScheme;

    return Scaffold(
      appBar: AppBar(
        title: const Text('Dienste'),
        actions: [
          IconButton(
            icon: const Icon(Icons.refresh),
            tooltip: 'Aktualisieren',
            onPressed: () => ref.read(shiftProvider.notifier).refresh(),
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
              const Text('Dienste konnten nicht geladen werden'),
              const SizedBox(height: 8),
              FilledButton(
                onPressed: () => ref.invalidate(shiftProvider),
                child: const Text('Erneut versuchen'),
              ),
            ],
          ),
        ),
        data: (data) {
          final types = data['types'] as List<ShiftType>? ?? [];
          final entries = data['entries'] as List<ShiftEntry>? ?? [];
          return _buildContent(types, entries, cs);
        },
      ),
    );
  }

  Widget _buildContent(List<ShiftType> types, List<ShiftEntry> entries, ColorScheme cs) {
    final entryMap = <String, List<ShiftEntry>>{};
    for (final e in entries) {
      entryMap.putIfAbsent(e.date, () => []).add(e);
    }

    final daysInMonth = DateTime(_year, _month + 1, 0).day;
    final startWeekday = DateTime(_year, _month, 1).weekday;

    return ListView(
      padding: const EdgeInsets.all(16),
      children: [
        // Month navigation
        Row(
          mainAxisAlignment: MainAxisAlignment.spaceBetween,
          children: [
            IconButton(icon: const Icon(Icons.chevron_left), onPressed: _prevMonth),
            Text(_monthLabel, style: Theme.of(context).textTheme.titleMedium),
            IconButton(icon: const Icon(Icons.chevron_right), onPressed: _nextMonth),
          ],
        ),
        const SizedBox(height: 8),

        // Weekday headers
        Row(
          children: ['Mo', 'Di', 'Mi', 'Do', 'Fr', 'Sa', 'So']
              .map((d) => Expanded(
                    child: Center(
                      child: Text(d, style: TextStyle(
                        fontWeight: FontWeight.bold,
                        color: cs.onSurfaceVariant,
                        fontSize: 12,
                      )),
                    ),
                  ))
              .toList(),
        ),
        const SizedBox(height: 4),

        // Calendar grid
        _buildCalendarGrid(daysInMonth, startWeekday, entryMap, types, cs),
        const SizedBox(height: 24),

        // Shift types management
        Row(
          mainAxisAlignment: MainAxisAlignment.spaceBetween,
          children: [
            Text('Diensttypen', style: Theme.of(context).textTheme.titleMedium),
            IconButton(
              icon: const Icon(Icons.add),
              tooltip: 'Neuer Typ',
              onPressed: () => _showAddTypeDialog(context),
            ),
          ],
        ),
        const SizedBox(height: 8),
        if (types.isEmpty)
          const Card(
            child: Padding(
              padding: EdgeInsets.all(16),
              child: Text('Keine Diensttypen vorhanden', style: TextStyle(color: Colors.grey)),
            ),
          )
        else
          ...types.map((t) => Card(
                child: ListTile(
                  leading: Container(
                    width: 24,
                    height: 24,
                    decoration: BoxDecoration(
                      color: _parseColor(t.color),
                      shape: BoxShape.circle,
                    ),
                  ),
                  title: Text(t.name),
                  subtitle: Text(_categoryLabel(t.category)),
                  trailing: IconButton(
                    icon: const Icon(Icons.delete_outline, size: 20),
                    onPressed: () => _confirmDeleteType(t),
                  ),
                ),
              )),
      ],
    );
  }

  Widget _buildCalendarGrid(
    int daysInMonth,
    int startWeekday,
    Map<String, List<ShiftEntry>> entryMap,
    List<ShiftType> types,
    ColorScheme cs,
  ) {
    final cells = <Widget>[];
    for (var i = 1; i < startWeekday; i++) {
      cells.add(const SizedBox());
    }
    for (var day = 1; day <= daysInMonth; day++) {
      final dateStr = '$_year-${_month.toString().padLeft(2, '0')}-${day.toString().padLeft(2, '0')}';
      final dayEntries = entryMap[dateStr] ?? [];

      cells.add(
        InkWell(
          borderRadius: BorderRadius.circular(8),
          onTap: () => _showDayDialog(dateStr, dayEntries, types),
          child: Container(
            decoration: BoxDecoration(
              borderRadius: BorderRadius.circular(8),
              color: dayEntries.isNotEmpty
                  ? cs.primaryContainer.withAlpha(80)
                  : null,
            ),
            child: Column(
              mainAxisAlignment: MainAxisAlignment.center,
              children: [
                Text(
                  '$day',
                  style: TextStyle(
                    fontSize: 14,
                    fontWeight: dayEntries.isNotEmpty ? FontWeight.bold : FontWeight.normal,
                  ),
                ),
                if (dayEntries.isNotEmpty)
                  Row(
                    mainAxisAlignment: MainAxisAlignment.center,
                    children: dayEntries
                        .take(3)
                        .map((e) => Container(
                              width: 6,
                              height: 6,
                              margin: const EdgeInsets.only(top: 2, right: 1),
                              decoration: BoxDecoration(
                                color: _parseColor(e.shiftTypeColor),
                                shape: BoxShape.circle,
                              ),
                            ))
                        .toList(),
                  ),
              ],
            ),
          ),
        ),
      );
    }

    return GridView.count(
      crossAxisCount: 7,
      shrinkWrap: true,
      physics: const NeverScrollableScrollPhysics(),
      childAspectRatio: 1.2,
      children: cells,
    );
  }

  void _showDayDialog(String date, List<ShiftEntry> entries, List<ShiftType> types) {
    showDialog(
      context: context,
      builder: (ctx) => AlertDialog(
        title: Text(date),
        content: SizedBox(
          width: double.maxFinite,
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              if (entries.isNotEmpty) ...[
                const Text('Eingetragene Dienste:', style: TextStyle(fontWeight: FontWeight.bold)),
                const SizedBox(height: 8),
                ...entries.map((e) => ListTile(
                      dense: true,
                      leading: Container(
                        width: 16,
                        height: 16,
                        decoration: BoxDecoration(
                          color: _parseColor(e.shiftTypeColor),
                          shape: BoxShape.circle,
                        ),
                      ),
                      title: Text(e.shiftTypeName ?? 'Dienst #${e.shiftTypeId}'),
                      trailing: IconButton(
                        icon: const Icon(Icons.close, size: 18),
                        onPressed: () {
                          Navigator.pop(ctx);
                          ref.read(shiftProvider.notifier).deleteEntry(e.id);
                        },
                      ),
                    )),
                const Divider(),
              ],
              if (types.isNotEmpty) ...[
                const Text('Dienst hinzufuegen:', style: TextStyle(fontWeight: FontWeight.bold)),
                const SizedBox(height: 8),
                ...types.map((t) => ListTile(
                      dense: true,
                      leading: Container(
                        width: 16,
                        height: 16,
                        decoration: BoxDecoration(
                          color: _parseColor(t.color),
                          shape: BoxShape.circle,
                        ),
                      ),
                      title: Text(t.name),
                      onTap: () {
                        Navigator.pop(ctx);
                        ref.read(shiftProvider.notifier).addEntry(
                              date: date,
                              shiftTypeId: t.id,
                            );
                      },
                    )),
              ] else
                const Text('Bitte zuerst Diensttypen anlegen.', style: TextStyle(color: Colors.grey)),
            ],
          ),
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(ctx),
            child: const Text('Schliessen'),
          ),
        ],
      ),
    );
  }

  void _showAddTypeDialog(BuildContext context) {
    final nameCtrl = TextEditingController();
    String selectedColor = '#4CAF50';
    String selectedCategory = 'work';

    final colors = {
      '#4CAF50': 'Gruen',
      '#2196F3': 'Blau',
      '#F44336': 'Rot',
      '#FF9800': 'Orange',
      '#9C27B0': 'Lila',
      '#607D8B': 'Grau',
    };

    final categories = {
      'work': 'Arbeit',
      'free': 'Frei',
      'vacation': 'Urlaub',
      'special': 'Sonder',
    };

    showDialog(
      context: context,
      builder: (ctx) => StatefulBuilder(
        builder: (ctx, setDialogState) => AlertDialog(
          title: const Text('Neuer Diensttyp'),
          content: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              TextField(
                controller: nameCtrl,
                decoration: const InputDecoration(
                  labelText: 'Name',
                  border: OutlineInputBorder(),
                ),
              ),
              const SizedBox(height: 12),
              DropdownButtonFormField<String>(
                value: selectedColor,
                decoration: const InputDecoration(
                  labelText: 'Farbe',
                  border: OutlineInputBorder(),
                ),
                items: colors.entries
                    .map((e) => DropdownMenuItem(
                          value: e.key,
                          child: Row(
                            children: [
                              Container(
                                width: 16,
                                height: 16,
                                decoration: BoxDecoration(
                                  color: _parseColor(e.key),
                                  shape: BoxShape.circle,
                                ),
                              ),
                              const SizedBox(width: 8),
                              Text(e.value),
                            ],
                          ),
                        ))
                    .toList(),
                onChanged: (v) => setDialogState(() => selectedColor = v!),
              ),
              const SizedBox(height: 12),
              DropdownButtonFormField<String>(
                value: selectedCategory,
                decoration: const InputDecoration(
                  labelText: 'Kategorie',
                  border: OutlineInputBorder(),
                ),
                items: categories.entries
                    .map((e) => DropdownMenuItem(value: e.key, child: Text(e.value)))
                    .toList(),
                onChanged: (v) => setDialogState(() => selectedCategory = v!),
              ),
            ],
          ),
          actions: [
            TextButton(
              onPressed: () => Navigator.pop(ctx),
              child: const Text('Abbrechen'),
            ),
            FilledButton(
              onPressed: () {
                final name = nameCtrl.text.trim();
                if (name.isEmpty) return;
                Navigator.pop(ctx);
                ref.read(shiftProvider.notifier).addType(
                      name: name,
                      color: selectedColor,
                      category: selectedCategory,
                    );
              },
              child: const Text('Erstellen'),
            ),
          ],
        ),
      ),
    );
  }

  void _confirmDeleteType(ShiftType type) {
    showDialog(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text('Diensttyp loeschen?'),
        content: Text('${type.name} wirklich loeschen?'),
        actions: [
          TextButton(onPressed: () => Navigator.pop(ctx), child: const Text('Abbrechen')),
          FilledButton(
            onPressed: () {
              Navigator.pop(ctx);
              ref.read(shiftProvider.notifier).deleteType(type.id);
            },
            child: const Text('Loeschen'),
          ),
        ],
      ),
    );
  }

  String _categoryLabel(String category) => switch (category) {
        'work' => 'Arbeit',
        'free' => 'Frei',
        'vacation' => 'Urlaub',
        'special' => 'Sonder',
        _ => category,
      };
}
