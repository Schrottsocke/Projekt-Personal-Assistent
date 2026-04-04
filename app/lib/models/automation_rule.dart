class AutomationRule {
  final int id;
  final String name;
  final String? description;
  final Map<String, dynamic> trigger;
  final Map<String, dynamic> action;
  final bool active;
  final int triggerCount;
  final DateTime? lastTriggered;
  final DateTime createdAt;

  const AutomationRule({
    required this.id,
    required this.name,
    this.description,
    required this.trigger,
    required this.action,
    required this.active,
    required this.triggerCount,
    this.lastTriggered,
    required this.createdAt,
  });

  factory AutomationRule.fromJson(Map<String, dynamic> j) => AutomationRule(
        id: j['id'] as int,
        name: j['name'] as String,
        description: j['description'] as String?,
        trigger: j['trigger'] as Map<String, dynamic>? ?? {},
        action: j['action'] as Map<String, dynamic>? ?? {},
        active: j['active'] as bool? ?? true,
        triggerCount: j['trigger_count'] as int? ?? 0,
        lastTriggered: j['last_triggered'] != null
            ? DateTime.parse(j['last_triggered'] as String)
            : null,
        createdAt: DateTime.parse(j['created_at'] as String),
      );
}
