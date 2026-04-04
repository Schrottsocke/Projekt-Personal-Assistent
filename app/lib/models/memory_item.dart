class MemoryItem {
  final String id;
  final String content;
  final Map<String, dynamic>? metadata;
  final DateTime? createdAt;

  const MemoryItem({
    required this.id,
    required this.content,
    this.metadata,
    this.createdAt,
  });

  factory MemoryItem.fromJson(Map<String, dynamic> j) => MemoryItem(
        id: j['id'] as String,
        content: j['memory'] as String? ?? j['content'] as String? ?? '',
        metadata: j['metadata'] as Map<String, dynamic>?,
        createdAt: j['created_at'] != null
            ? DateTime.parse(j['created_at'] as String)
            : null,
      );
}
