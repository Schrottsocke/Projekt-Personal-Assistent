class Task {
  final int id;
  final String userKey;
  final String title;
  final String description;
  final String priority;
  final String status;
  final DateTime? dueDate;
  final String? assignedBy;
  final DateTime createdAt;
  final String? recurrence;
  final DateTime? lastCompleted;

  const Task({
    required this.id,
    required this.userKey,
    required this.title,
    required this.description,
    required this.priority,
    required this.status,
    this.dueDate,
    this.assignedBy,
    required this.createdAt,
    this.recurrence,
    this.lastCompleted,
  });

  factory Task.fromJson(Map<String, dynamic> j) => Task(
        id: j['id'] as int,
        userKey: j['user_key'] as String,
        title: j['title'] as String,
        description: j['description'] ?? '',
        priority: j['priority'] ?? 'medium',
        status: j['status'] ?? 'open',
        dueDate: j['due_date'] != null ? DateTime.parse(j['due_date'] as String) : null,
        assignedBy: j['assigned_by'] as String?,
        createdAt: DateTime.parse(j['created_at'] as String),
        recurrence: j['recurrence'] as String?,
        lastCompleted: j['last_completed'] != null
            ? DateTime.parse(j['last_completed'] as String)
            : null,
      );

  String get priorityLabel => switch (priority) {
        'high' => '🔴 Hoch',
        'low' => '🟢 Niedrig',
        _ => '🟡 Mittel',
      };

  String get statusLabel => switch (status) {
        'done' => 'Erledigt',
        'in_progress' => 'In Bearbeitung',
        _ => 'Offen',
      };

  bool get isDone => status == 'done';
  bool get isInProgress => status == 'in_progress';
  bool get isRecurring => recurrence != null;
}
