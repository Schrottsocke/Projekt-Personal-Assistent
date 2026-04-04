class ShiftType {
  final int id;
  final String name;
  final String color;
  final String category;

  const ShiftType({
    required this.id,
    required this.name,
    required this.color,
    required this.category,
  });

  factory ShiftType.fromJson(Map<String, dynamic> j) => ShiftType(
        id: j['id'] as int,
        name: j['name'] as String,
        color: j['color'] as String? ?? '#808080',
        category: j['category'] as String? ?? 'work',
      );
}

class ShiftEntry {
  final int id;
  final String date;
  final int shiftTypeId;
  final String? shiftTypeName;
  final String? shiftTypeColor;
  final String? notes;

  const ShiftEntry({
    required this.id,
    required this.date,
    required this.shiftTypeId,
    this.shiftTypeName,
    this.shiftTypeColor,
    this.notes,
  });

  factory ShiftEntry.fromJson(Map<String, dynamic> j) => ShiftEntry(
        id: j['id'] as int,
        date: j['date'] as String,
        shiftTypeId: j['shift_type_id'] as int,
        shiftTypeName: j['shift_type_name'] as String?,
        shiftTypeColor: j['shift_type_color'] as String?,
        notes: j['notes'] as String?,
      );
}
