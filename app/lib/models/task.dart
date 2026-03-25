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
      );

  String get priorityLabel => switch (priority) {
        'high' => '🔴 Hoch',
        'low' => '🟢 Niedrig',
        _ => '🟡 Mittel',
      };

  bool get isDone => status == 'done';
}
