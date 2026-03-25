class ChatMessage {
  final int? id;
  final String role;
  final String content;
  final DateTime? createdAt;

  const ChatMessage({
    this.id,
    required this.role,
    required this.content,
    this.createdAt,
  });

  factory ChatMessage.fromJson(Map<String, dynamic> j) => ChatMessage(
        id: j['id'] as int?,
        role: j['role'] as String,
        content: j['content'] as String,
        createdAt: j['created_at'] != null
            ? DateTime.parse(j['created_at'] as String)
            : null,
      );

  bool get isUser => role == 'user';
  bool get isAssistant => role == 'assistant';
}
