class InboxItem {
  final int id;
  final String title;
  final String? body;
  final String category;
  final String status;
  final String? priority;
  final List<String> actions;
  final DateTime createdAt;

  const InboxItem({
    required this.id,
    required this.title,
    this.body,
    required this.category,
    required this.status,
    this.priority,
    required this.actions,
    required this.createdAt,
  });

  factory InboxItem.fromJson(Map<String, dynamic> j) => InboxItem(
        id: j['id'] as int,
        title: j['title'] as String,
        body: j['body'] as String?,
        category: j['category'] as String? ?? 'proposal',
        status: j['status'] as String? ?? 'pending',
        priority: j['priority'] as String?,
        actions: (j['actions'] as List?)?.cast<String>() ?? [],
        createdAt: DateTime.parse(j['created_at'] as String),
      );
}
