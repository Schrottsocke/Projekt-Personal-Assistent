class FollowUp {
  final int id;
  final String title;
  final String type; // reminder, check_in, deadline, custom
  final String status; // open, done, cancelled
  final DateTime? dueDate;
  final String? notes;
  final String? reference;
  final DateTime createdAt;

  const FollowUp({
    required this.id,
    required this.title,
    required this.type,
    required this.status,
    this.dueDate,
    this.notes,
    this.reference,
    required this.createdAt,
  });

  factory FollowUp.fromJson(Map<String, dynamic> j) => FollowUp(
        id: j['id'] as int,
        title: j['title'] as String,
        type: j['type'] as String? ?? 'custom',
        status: j['status'] as String? ?? 'open',
        dueDate: j['due_date'] != null
            ? DateTime.parse(j['due_date'] as String)
            : null,
        notes: j['notes'] as String?,
        reference: j['reference'] as String?,
        createdAt: DateTime.parse(j['created_at'] as String),
      );

  bool get isOverdue =>
      status == 'open' &&
      dueDate != null &&
      dueDate!.isBefore(DateTime.now());

  String get typeLabel => switch (type) {
        'reminder' => 'Erinnerung',
        'check_in' => 'Nachfrage',
        'deadline' => 'Frist',
        _ => 'Eigenes',
      };

  String get statusLabel => switch (status) {
        'done' => 'Erledigt',
        'cancelled' => 'Abgebrochen',
        _ => 'Offen',
      };
}
