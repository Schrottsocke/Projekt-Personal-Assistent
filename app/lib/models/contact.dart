class Contact {
  final int id;
  final String name;
  final String? email;
  final String? phone;
  final String? notes;
  final List<String> tags;
  final String? source;
  final DateTime? lastInteraction;
  final DateTime createdAt;

  const Contact({
    required this.id,
    required this.name,
    this.email,
    this.phone,
    this.notes,
    required this.tags,
    this.source,
    this.lastInteraction,
    required this.createdAt,
  });

  factory Contact.fromJson(Map<String, dynamic> j) => Contact(
        id: j['id'] as int,
        name: j['name'] as String,
        email: j['email'] as String?,
        phone: j['phone'] as String?,
        notes: j['notes'] as String?,
        tags: (j['tags'] as List<dynamic>?)?.map((e) => e as String).toList() ?? [],
        source: j['source'] as String?,
        lastInteraction: j['last_interaction'] != null
            ? DateTime.parse(j['last_interaction'] as String)
            : null,
        createdAt: DateTime.parse(j['created_at'] as String),
      );
}
