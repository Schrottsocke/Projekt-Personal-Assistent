import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../providers/calendar_provider.dart';
import '../models/calendar_event.dart';
import '../widgets/event_card.dart';

class CalendarScreen extends ConsumerStatefulWidget {
  const CalendarScreen({super.key});
  @override
  ConsumerState<CalendarScreen> createState() => _CalendarScreenState();
}

class _CalendarScreenState extends ConsumerState<CalendarScreen> with SingleTickerProviderStateMixin {
  late final TabController _tabs;

  @override
  void initState() {
    super.initState();
    _tabs = TabController(length: 2, vsync: this);
  }

  @override
  void dispose() {
    _tabs.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Kalender'),
        bottom: TabBar(controller: _tabs, tabs: const [Tab(text: 'Heute'), Tab(text: 'Woche')]),
        actions: [
          IconButton(
            icon: const Icon(Icons.refresh),
            tooltip: 'Aktualisieren',
            onPressed: () {
              ref.read(calendarTodayProvider.notifier).refresh();
              ref.read(calendarWeekProvider.notifier).refresh();
            },
          ),
        ],
      ),
      body: TabBarView(
        controller: _tabs,
        children: const [_TodayTab(), _WeekTab()],
      ),
      floatingActionButton: FloatingActionButton(
        onPressed: () => _showCreateEventDialog(context),
        tooltip: 'Neuer Termin',
        child: const Icon(Icons.add),
      ),
    );
  }

  void _showCreateEventDialog(BuildContext context) {
    showModalBottomSheet(
      context: context,
      isScrollControlled: true,
      useSafeArea: true,
      builder: (_) => const _CreateEventSheet(),
    );
  }
}

class _TodayTab extends ConsumerWidget {
  const _TodayTab();

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final state = ref.watch(calendarTodayProvider);
    return state.when(
      loading: () => const Center(child: CircularProgressIndicator()),
      error: (e, _) => Center(child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          const Icon(Icons.cloud_off, size: 48, color: Colors.grey),
          const SizedBox(height: 16),
          const Text('Termine konnten nicht geladen werden'),
          const SizedBox(height: 8),
          FilledButton(
            onPressed: () => ref.invalidate(calendarTodayProvider),
            child: const Text('Erneut versuchen'),
          ),
        ],
      )),
      data: (events) => events.isEmpty
          ? const Center(child: Text('Keine Termine heute', style: TextStyle(color: Colors.grey)))
          : RefreshIndicator(
              onRefresh: () async => ref.read(calendarTodayProvider.notifier).refresh(),
              child: ListView.builder(
                padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
                itemCount: events.length,
                itemBuilder: (_, i) => EventCard(event: events[i]),
              ),
            ),
    );
  }
}

class _WeekTab extends ConsumerWidget {
  const _WeekTab();

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final state = ref.watch(calendarWeekProvider);
    return state.when(
      loading: () => const Center(child: CircularProgressIndicator()),
      error: (e, _) => Center(child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          const Icon(Icons.cloud_off, size: 48, color: Colors.grey),
          const SizedBox(height: 16),
          const Text('Wochenuebersicht konnte nicht geladen werden'),
          const SizedBox(height: 8),
          FilledButton(
            onPressed: () => ref.invalidate(calendarWeekProvider),
            child: const Text('Erneut versuchen'),
          ),
        ],
      )),
      data: (events) => events.isEmpty
          ? const Center(child: Text('Keine Termine diese Woche', style: TextStyle(color: Colors.grey)))
          : RefreshIndicator(
              onRefresh: () async => ref.read(calendarWeekProvider.notifier).refresh(),
              child: _buildGroupedList(events),
            ),
    );
  }

  Widget _buildGroupedList(List<CalendarEvent> events) {
    final Map<String, List<CalendarEvent>> grouped = {};
    for (final event in events) {
      final dt = event.startTime;
      final key = dt != null
          ? '${_weekdayName(dt.weekday)}, ${dt.day}.${dt.month}.'
          : 'Unbekannt';
      grouped.putIfAbsent(key, () => []).add(event);
    }

    return ListView(
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
      children: grouped.entries.map((entry) => Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Padding(
            padding: const EdgeInsets.fromLTRB(4, 12, 4, 4),
            child: Text(entry.key, style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 13, color: Colors.grey)),
          ),
          ...entry.value.map((e) => EventCard(event: e)),
        ],
      )).toList(),
    );
  }

  String _weekdayName(int weekday) => switch (weekday) {
    1 => 'Montag',
    2 => 'Dienstag',
    3 => 'Mittwoch',
    4 => 'Donnerstag',
    5 => 'Freitag',
    6 => 'Samstag',
    7 => 'Sonntag',
    _ => '',
  };
}

class _CreateEventSheet extends ConsumerStatefulWidget {
  const _CreateEventSheet();
  @override
  ConsumerState<_CreateEventSheet> createState() => _CreateEventSheetState();
}

class _CreateEventSheetState extends ConsumerState<_CreateEventSheet> {
  final _summaryCtrl = TextEditingController();
  final _descriptionCtrl = TextEditingController();
  final _locationCtrl = TextEditingController();
  DateTime _startDate = DateTime.now();
  TimeOfDay _startTime = TimeOfDay.now();
  TimeOfDay _endTime = TimeOfDay(hour: TimeOfDay.now().hour + 1, minute: TimeOfDay.now().minute);
  bool _saving = false;

  @override
  void dispose() {
    _summaryCtrl.dispose();
    _descriptionCtrl.dispose();
    _locationCtrl.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return DraggableScrollableSheet(
      expand: false,
      initialChildSize: 0.75,
      builder: (_, ctrl) => ListView(
        controller: ctrl,
        padding: const EdgeInsets.all(16),
        children: [
          Text('Neuer Termin', style: Theme.of(context).textTheme.titleLarge?.copyWith(fontWeight: FontWeight.bold)),
          const SizedBox(height: 16),
          TextField(
            controller: _summaryCtrl,
            decoration: const InputDecoration(labelText: 'Titel', border: OutlineInputBorder()),
          ),
          const SizedBox(height: 12),
          Row(
            children: [
              Expanded(
                child: OutlinedButton.icon(
                  icon: const Icon(Icons.calendar_today, size: 16),
                  label: Text('${_startDate.day}.${_startDate.month}.${_startDate.year}'),
                  onPressed: () async {
                    final picked = await showDatePicker(
                      context: context,
                      initialDate: _startDate,
                      firstDate: DateTime.now().subtract(const Duration(days: 30)),
                      lastDate: DateTime.now().add(const Duration(days: 365)),
                    );
                    if (picked != null) setState(() => _startDate = picked);
                  },
                ),
              ),
              const SizedBox(width: 8),
              OutlinedButton(
                onPressed: () async {
                  final picked = await showTimePicker(context: context, initialTime: _startTime);
                  if (picked != null) setState(() => _startTime = picked);
                },
                child: Text('${_startTime.hour.toString().padLeft(2, '0')}:${_startTime.minute.toString().padLeft(2, '0')}'),
              ),
              const Padding(padding: EdgeInsets.symmetric(horizontal: 4), child: Text('-')),
              OutlinedButton(
                onPressed: () async {
                  final picked = await showTimePicker(context: context, initialTime: _endTime);
                  if (picked != null) setState(() => _endTime = picked);
                },
                child: Text('${_endTime.hour.toString().padLeft(2, '0')}:${_endTime.minute.toString().padLeft(2, '0')}'),
              ),
            ],
          ),
          const SizedBox(height: 12),
          TextField(
            controller: _locationCtrl,
            decoration: const InputDecoration(labelText: 'Ort (optional)', border: OutlineInputBorder(), isDense: true),
          ),
          const SizedBox(height: 12),
          TextField(
            controller: _descriptionCtrl,
            decoration: const InputDecoration(labelText: 'Beschreibung (optional)', border: OutlineInputBorder(), isDense: true),
            maxLines: 3,
          ),
          const SizedBox(height: 24),
          FilledButton(
            onPressed: _saving ? null : _createEvent,
            child: _saving
                ? const SizedBox(width: 20, height: 20, child: CircularProgressIndicator(strokeWidth: 2))
                : const Text('Termin erstellen'),
          ),
        ],
      ),
    );
  }

  Future<void> _createEvent() async {
    final summary = _summaryCtrl.text.trim();
    if (summary.isEmpty) return;
    setState(() => _saving = true);

    final start = DateTime(_startDate.year, _startDate.month, _startDate.day, _startTime.hour, _startTime.minute);
    final end = DateTime(_startDate.year, _startDate.month, _startDate.day, _endTime.hour, _endTime.minute);

    try {
      await ref.read(calendarServiceProvider).createEvent(
        summary: summary,
        start: start.toIso8601String(),
        end: end.toIso8601String(),
        description: _descriptionCtrl.text.trim(),
        location: _locationCtrl.text.trim(),
      );
      ref.read(calendarTodayProvider.notifier).refresh();
      ref.read(calendarWeekProvider.notifier).refresh();
      if (mounted) {
        Navigator.pop(context);
        ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text('Termin erstellt!')));
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text('Fehler: $e')));
      }
    } finally {
      if (mounted) setState(() => _saving = false);
    }
  }
}
