import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import '../providers/task_provider.dart';
import '../providers/shopping_provider.dart';
import '../providers/followup_provider.dart';

/// Detected capture type for quick input.
enum CaptureType { task, shopping, reminder, calendar }

class QuickCaptureSheet extends ConsumerStatefulWidget {
  const QuickCaptureSheet({super.key});
  @override
  ConsumerState<QuickCaptureSheet> createState() => _QuickCaptureSheetState();
}

class _QuickCaptureSheetState extends ConsumerState<QuickCaptureSheet> {
  final _controller = TextEditingController();
  CaptureType _type = CaptureType.task;
  bool _submitting = false;

  @override
  void initState() {
    super.initState();
    _controller.addListener(_detectType);
  }

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  void _detectType() {
    final text = _controller.text.toLowerCase().trim();
    final detected = _detectFromText(text);
    if (detected != _type) {
      setState(() => _type = detected);
    }
  }

  CaptureType _detectFromText(String text) {
    if (text.startsWith('kaufe') ||
        text.startsWith('kauf ') ||
        text.startsWith('einkauf')) {
      return CaptureType.shopping;
    }
    if (text.startsWith('erinnere') || text.startsWith('reminder')) {
      return CaptureType.reminder;
    }
    if (text.startsWith('termin') || text.startsWith('meeting')) {
      return CaptureType.calendar;
    }
    return CaptureType.task;
  }

  String _typeLabel(CaptureType t) => switch (t) {
        CaptureType.task => 'Aufgabe',
        CaptureType.shopping => 'Einkauf',
        CaptureType.reminder => 'Follow-up',
        CaptureType.calendar => 'Kalender',
      };

  IconData _typeIcon(CaptureType t) => switch (t) {
        CaptureType.task => Icons.check_box,
        CaptureType.shopping => Icons.shopping_cart,
        CaptureType.reminder => Icons.alarm,
        CaptureType.calendar => Icons.event,
      };

  Future<void> _submit() async {
    final text = _controller.text.trim();
    if (text.isEmpty) return;

    setState(() => _submitting = true);

    try {
      String successMsg;
      String? navRoute;

      switch (_type) {
        case CaptureType.shopping:
          await ref.read(shoppingProvider.notifier).addItem(text);
          successMsg = 'Einkauf hinzugefuegt';
          navRoute = '/shopping';
        case CaptureType.reminder:
          await ref.read(followUpProvider.notifier).create(title: text, type: 'reminder');
          successMsg = 'Follow-up erstellt';
          navRoute = '/followups';
        case CaptureType.calendar:
          // Calendar creation requires more fields; create as task with hint
          await ref.read(taskProvider.notifier).addTask(text);
          successMsg = 'Als Aufgabe erstellt (Termin im Chat anlegen)';
          navRoute = '/tasks';
        case CaptureType.task:
          await ref.read(taskProvider.notifier).addTask(text);
          successMsg = 'Aufgabe erstellt';
          navRoute = '/tasks';
      }

      if (mounted) {
        Navigator.pop(context);
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text(successMsg),
            action: navRoute != null
                ? SnackBarAction(
                    label: 'Anzeigen',
                    onPressed: () => context.go(navRoute!),
                  )
                : null,
          ),
        );
      }
    } catch (e) {
      if (mounted) {
        setState(() => _submitting = false);
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Fehler: $e')),
        );
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: EdgeInsets.only(
        bottom: MediaQuery.of(context).viewInsets.bottom,
        left: 16,
        right: 16,
        top: 16,
      ),
      child: Column(
        mainAxisSize: MainAxisSize.min,
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          Row(
            children: [
              const Icon(Icons.add, size: 20),
              const SizedBox(width: 8),
              const Text(
                'Schnelleingabe',
                style: TextStyle(fontWeight: FontWeight.bold, fontSize: 16),
              ),
              const Spacer(),
              IconButton(
                icon: const Icon(Icons.close),
                onPressed: () => Navigator.pop(context),
              ),
            ],
          ),
          const SizedBox(height: 12),
          TextField(
            controller: _controller,
            autofocus: true,
            decoration: const InputDecoration(
              hintText: 'Was moechtest du erfassen?',
              border: OutlineInputBorder(),
            ),
            onSubmitted: (_) => _submit(),
          ),
          const SizedBox(height: 12),
          Wrap(
            spacing: 8,
            children: CaptureType.values.map((t) {
              return ChoiceChip(
                avatar: Icon(_typeIcon(t), size: 16),
                label: Text(_typeLabel(t)),
                selected: _type == t,
                onSelected: (_) => setState(() => _type = t),
              );
            }).toList(),
          ),
          const SizedBox(height: 16),
          FilledButton(
            onPressed: _submitting ? null : _submit,
            child: _submitting
                ? const SizedBox(
                    height: 20,
                    width: 20,
                    child: CircularProgressIndicator(strokeWidth: 2),
                  )
                : Text('${_typeLabel(_type)} erstellen'),
          ),
          const SizedBox(height: 16),
        ],
      ),
    );
  }
}
