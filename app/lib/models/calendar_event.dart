class CalendarEvent {
  final String? id;
  final String summary;
  final String start;
  final String end;
  final String description;
  final String location;

  const CalendarEvent({
    this.id,
    required this.summary,
    required this.start,
    required this.end,
    this.description = '',
    this.location = '',
  });

  factory CalendarEvent.fromJson(Map<String, dynamic> j) => CalendarEvent(
        id: j['id'] as String?,
        summary: j['summary'] as String? ?? '',
        start: j['start'] as String? ?? '',
        end: j['end'] as String? ?? '',
        description: j['description'] as String? ?? '',
        location: j['location'] as String? ?? '',
      );

  DateTime? get startTime {
    try {
      return DateTime.parse(start);
    } catch (_) {
      return null;
    }
  }

  String get timeLabel {
    final dt = startTime;
    if (dt == null) return start;
    return '${dt.hour.toString().padLeft(2, '0')}:${dt.minute.toString().padLeft(2, '0')} Uhr';
  }
}
