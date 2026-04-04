class ShiftType {
  final int id;
  final String name;
  final String color;
  final String category;
  final String? shortName;
  final String? startTime;
  final String? endTime;
  final int? breakMinutes;

  const ShiftType({
    required this.id,
    required this.name,
    required this.color,
    required this.category,
    this.shortName,
    this.startTime,
    this.endTime,
    this.breakMinutes,
  });

  factory ShiftType.fromJson(Map<String, dynamic> j) => ShiftType(
        id: j['id'] as int,
        name: j['name'] as String,
        color: j['color'] as String? ?? '#808080',
        category: j['category'] as String? ?? 'work',
        shortName: j['short_name'] as String?,
        startTime: j['start_time'] as String?,
        endTime: j['end_time'] as String?,
        breakMinutes: j['break_minutes'] as int?,
      );
}

class ShiftEntry {
  final int id;
  final String date;
  final int shiftTypeId;
  final String? shiftTypeName;
  final String? shiftTypeColor;
  final String? shiftTypeShortName;
  final String? notes;

  // Soll-Zeiten (Override)
  final String? plannedStart;
  final String? plannedEnd;
  final int? breakMinutes;

  // Ist-Zeiten
  final String? actualStart;
  final String? actualEnd;
  final int? actualBreakMinutes;

  // Berechnete Dauern
  final int? plannedDurationMinutes;
  final int? actualDurationMinutes;
  final int? deltaMinutes;

  // Bestaetigungsstatus
  final String confirmationStatus;
  final String? confirmationSource;
  final String? confirmationTimestamp;
  final String? deviationNote;

  // Reminder
  final bool reminderSent;
  final int reminderCount;

  const ShiftEntry({
    required this.id,
    required this.date,
    required this.shiftTypeId,
    this.shiftTypeName,
    this.shiftTypeColor,
    this.shiftTypeShortName,
    this.notes,
    this.plannedStart,
    this.plannedEnd,
    this.breakMinutes,
    this.actualStart,
    this.actualEnd,
    this.actualBreakMinutes,
    this.plannedDurationMinutes,
    this.actualDurationMinutes,
    this.deltaMinutes,
    this.confirmationStatus = 'pending',
    this.confirmationSource,
    this.confirmationTimestamp,
    this.deviationNote,
    this.reminderSent = false,
    this.reminderCount = 0,
  });

  bool get isPending => confirmationStatus == 'pending';
  bool get isConfirmed => confirmationStatus == 'confirmed';
  bool get hasDeviation => confirmationStatus == 'deviation';
  bool get isCancelled => confirmationStatus == 'cancelled';

  factory ShiftEntry.fromJson(Map<String, dynamic> j) => ShiftEntry(
        id: j['id'] as int,
        date: j['date'] as String,
        shiftTypeId: j['shift_type_id'] as int,
        shiftTypeName: j['shift_type_name'] as String?,
        shiftTypeColor: j['shift_type_color'] as String?,
        shiftTypeShortName: j['shift_type_short_name'] as String?,
        notes: j['notes'] as String?,
        plannedStart: j['planned_start'] as String?,
        plannedEnd: j['planned_end'] as String?,
        breakMinutes: j['break_minutes'] as int?,
        actualStart: j['actual_start'] as String?,
        actualEnd: j['actual_end'] as String?,
        actualBreakMinutes: j['actual_break_minutes'] as int?,
        plannedDurationMinutes: j['planned_duration_minutes'] as int?,
        actualDurationMinutes: j['actual_duration_minutes'] as int?,
        deltaMinutes: j['delta_minutes'] as int?,
        confirmationStatus: j['confirmation_status'] as String? ?? 'pending',
        confirmationSource: j['confirmation_source'] as String?,
        confirmationTimestamp: j['confirmation_timestamp'] as String?,
        deviationNote: j['deviation_note'] as String?,
        reminderSent: j['reminder_sent'] as bool? ?? false,
        reminderCount: j['reminder_count'] as int? ?? 0,
      );
}

class ShiftReportSummary {
  final double plannedHours;
  final double actualHours;
  final double deltaHours;
  final int confirmedCount;
  final int pendingCount;
  final int deviationCount;
  final int cancelledCount;

  const ShiftReportSummary({
    required this.plannedHours,
    required this.actualHours,
    required this.deltaHours,
    required this.confirmedCount,
    required this.pendingCount,
    required this.deviationCount,
    required this.cancelledCount,
  });

  int get totalCount =>
      confirmedCount + pendingCount + deviationCount + cancelledCount;

  factory ShiftReportSummary.fromJson(Map<String, dynamic> j) =>
      ShiftReportSummary(
        plannedHours: (j['planned_hours'] as num?)?.toDouble() ?? 0,
        actualHours: (j['actual_hours'] as num?)?.toDouble() ?? 0,
        deltaHours: (j['delta_hours'] as num?)?.toDouble() ?? 0,
        confirmedCount: j['confirmed_count'] as int? ?? 0,
        pendingCount: j['pending_count'] as int? ?? 0,
        deviationCount: j['deviation_count'] as int? ?? 0,
        cancelledCount: j['cancelled_count'] as int? ?? 0,
      );
}

class ShiftReport {
  final String month;
  final List<ShiftEntry> entries;
  final ShiftReportSummary summary;

  const ShiftReport({
    required this.month,
    required this.entries,
    required this.summary,
  });

  factory ShiftReport.fromJson(Map<String, dynamic> j) => ShiftReport(
        month: j['month'] as String,
        entries: (j['entries'] as List)
            .map((e) => ShiftEntry.fromJson(e as Map<String, dynamic>))
            .toList(),
        summary: ShiftReportSummary.fromJson(
            j['summary'] as Map<String, dynamic>),
      );
}
