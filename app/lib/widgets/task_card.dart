import 'package:flutter/material.dart';
import '../models/task.dart';

class TaskCard extends StatefulWidget {
  final Task task;
  final VoidCallback? onComplete;
  final VoidCallback? onDelete;
  final void Function(String status)? onStatusChange;
  final void Function(String title)? onTitleEdit;

  const TaskCard({
    super.key,
    required this.task,
    this.onComplete,
    this.onDelete,
    this.onStatusChange,
    this.onTitleEdit,
  });

  @override
  State<TaskCard> createState() => _TaskCardState();
}

class _TaskCardState extends State<TaskCard> {
  bool _editing = false;
  late TextEditingController _editCtrl;

  @override
  void initState() {
    super.initState();
    _editCtrl = TextEditingController(text: widget.task.title);
  }

  @override
  void didUpdateWidget(TaskCard old) {
    super.didUpdateWidget(old);
    if (old.task.title != widget.task.title) {
      _editCtrl.text = widget.task.title;
    }
  }

  @override
  void dispose() {
    _editCtrl.dispose();
    super.dispose();
  }

  void _cycleStatus() {
    if (widget.onStatusChange == null) return;
    final next = switch (widget.task.status) {
      'open' => 'in_progress',
      'in_progress' => 'done',
      _ => 'open',
    };
    widget.onStatusChange!(next);
  }

  IconData _statusIcon() => switch (widget.task.status) {
        'in_progress' => Icons.play_circle_outline,
        'done' => Icons.check_circle,
        _ => Icons.radio_button_unchecked,
      };

  Color _statusColor(BuildContext context) => switch (widget.task.status) {
        'in_progress' => Colors.blue.shade400,
        'done' => Colors.green.shade400,
        _ => Colors.grey.shade400,
      };

  void _submitEdit() {
    final newTitle = _editCtrl.text.trim();
    setState(() => _editing = false);
    if (newTitle.isNotEmpty && newTitle != widget.task.title && widget.onTitleEdit != null) {
      widget.onTitleEdit!(newTitle);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Card(
      margin: const EdgeInsets.symmetric(vertical: 4),
      child: ListTile(
        leading: _priorityIcon(),
        title: _editing
            ? TextField(
                controller: _editCtrl,
                autofocus: true,
                onSubmitted: (_) => _submitEdit(),
                decoration: const InputDecoration(
                  isDense: true,
                  border: InputBorder.none,
                  contentPadding: EdgeInsets.zero,
                ),
              )
            : GestureDetector(
                onLongPress: widget.onTitleEdit != null ? () => setState(() => _editing = true) : null,
                child: Row(
                  children: [
                    Flexible(
                      child: Text(
                        widget.task.title,
                        style: TextStyle(
                          decoration: widget.task.isDone ? TextDecoration.lineThrough : null,
                          color: widget.task.isDone ? Colors.grey : null,
                        ),
                      ),
                    ),
                    if (widget.task.isRecurring) ...[
                      const SizedBox(width: 6),
                      Tooltip(
                        message: _recurrenceLabel(widget.task.recurrence!),
                        child: Icon(Icons.repeat, size: 16, color: Theme.of(context).colorScheme.primary),
                      ),
                    ],
                  ],
                ),
              ),
        subtitle: widget.task.description.isNotEmpty
            ? Text(widget.task.description, maxLines: 1, overflow: TextOverflow.ellipsis)
            : null,
        trailing: Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            IconButton(
              icon: Icon(_statusIcon(), color: _statusColor(context)),
              onPressed: _cycleStatus,
              tooltip: widget.task.statusLabel,
            ),
            if (widget.onDelete != null)
              IconButton(icon: const Icon(Icons.delete_outline), onPressed: widget.onDelete, color: Colors.red.shade300, tooltip: 'Loeschen'),
          ],
        ),
      ),
    );
  }

  Widget _priorityIcon() {
    return Container(
      width: 10,
      height: 40,
      decoration: BoxDecoration(
        color: switch (widget.task.priority) {
          'high' => Colors.red.shade400,
          'low' => Colors.green.shade400,
          _ => Colors.orange.shade400,
        },
        borderRadius: BorderRadius.circular(4),
      ),
    );
  }

  String _recurrenceLabel(String recurrence) => switch (recurrence) {
        'daily' => 'Taeglich',
        'weekly' => 'Woechentlich',
        'monthly' => 'Monatlich',
        _ => recurrence,
      };
}
