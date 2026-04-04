class Template {
  final int id;
  final String name;
  final String category;
  final Map<String, dynamic> content;
  final DateTime createdAt;

  const Template({
    required this.id,
    required this.name,
    required this.category,
    required this.content,
    required this.createdAt,
  });

  factory Template.fromJson(Map<String, dynamic> j) => Template(
        id: j['id'] as int,
        name: j['name'] as String,
        category: j['category'] as String? ?? 'task',
        content: j['content'] as Map<String, dynamic>? ?? {},
        createdAt: DateTime.parse(j['created_at'] as String),
      );

  String get categoryLabel => switch (category) {
        'shopping' => 'Einkaufsliste',
        'task' => 'Aufgabe',
        'checklist' => 'Checkliste',
        'routine' => 'Routine',
        'mealplan' => 'Wochenplan',
        'message' => 'Nachricht',
        _ => category,
      };
}
