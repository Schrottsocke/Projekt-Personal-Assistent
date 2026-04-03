import '../config/api_config.dart';
import '../models/calendar_event.dart';
import 'api_service.dart';

class CalendarService {
  final ApiService _api;
  CalendarService(this._api);

  Future<List<CalendarEvent>> getToday() async {
    final resp = await _api.get(ApiConfig.calendarTodayPath);
    return (resp.data as List).map((e) => CalendarEvent.fromJson(e as Map<String, dynamic>)).toList();
  }

  Future<List<CalendarEvent>> getWeek() async {
    final resp = await _api.get(ApiConfig.calendarWeekPath);
    return (resp.data as List).map((e) => CalendarEvent.fromJson(e as Map<String, dynamic>)).toList();
  }

  Future<void> createEvent({
    required String summary,
    required String start,
    required String end,
    String description = '',
    String location = '',
  }) async {
    await _api.post(ApiConfig.calendarEventsPath, data: {
      'summary': summary,
      'start': start,
      'end': end,
      'description': description,
      'location': location,
    });
  }
}
