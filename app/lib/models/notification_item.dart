class NotificationItem {
  final int id;
  final String title;
  final String? body;
  final String type; // info, warning, success, error
  final String status; // unread, read, archived
  final DateTime createdAt;

  const NotificationItem({
    required this.id,
    required this.title,
    this.body,
    required this.type,
    required this.status,
    required this.createdAt,
  });

  factory NotificationItem.fromJson(Map<String, dynamic> j) => NotificationItem(
        id: j['id'] as int,
        title: j['title'] as String,
        body: j['body'] as String?,
        type: j['type'] as String? ?? 'info',
        status: j['status'] as String? ?? 'unread',
        createdAt: DateTime.parse(j['created_at'] as String),
      );
}
