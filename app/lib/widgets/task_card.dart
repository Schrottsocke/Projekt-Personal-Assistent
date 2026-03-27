import 'package:flutter/material.dart';
import '../models/task.dart';

class TaskCard extends StatelessWidget {
  final Task task;
  final VoidCallback? onComplete;
  final VoidCallback? onDelete;

  const TaskCard({super.key, required this.task, this.onComplete, this.onDelete});

  @override
  Widget build(BuildContext context) {
    return Card(
      margin: const EdgeInsets.symmetric(vertical: 4),
      child: ListTile(
        leading: _priorityIcon(),
        title: Text(
          task.title,
          style: TextStyle(
            decoration: task.isDone ? TextDecoration.lineThrough : null,
            color: task.isDone ? Colors.grey : null,
          ),
        ),
        subtitle: task.description.isNotEmpty ? Text(task.description, maxLines: 1, overflow: TextOverflow.ellipsis) : null,
        trailing: Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            if (!task.isDone && onComplete != null)
              IconButton(icon: const Icon(Icons.check_circle_outline), onPressed: onComplete, tooltip: 'Erledigt'),
            if (onDelete != null)
              IconButton(icon: const Icon(Icons.delete_outline), onPressed: onDelete, color: Colors.red.shade300, tooltip: 'Löschen'),
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
        color: switch (task.priority) {
          'high' => Colors.red.shade400,
          'low' => Colors.green.shade400,
          _ => Colors.orange.shade400,
        },
        borderRadius: BorderRadius.circular(4),
      ),
    );
  }
}
