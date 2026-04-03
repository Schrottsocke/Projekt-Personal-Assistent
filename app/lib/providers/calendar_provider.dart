import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../models/calendar_event.dart';
import '../services/calendar_service.dart';
import 'auth_provider.dart';

final calendarServiceProvider = Provider<CalendarService>((ref) {
  return CalendarService(ref.watch(apiServiceProvider));
});

class CalendarTodayNotifier extends AsyncNotifier<List<CalendarEvent>> {
  @override
  Future<List<CalendarEvent>> build() async {
    return ref.read(calendarServiceProvider).getToday();
  }

  Future<void> refresh() async {
    state = const AsyncLoading();
    state = await AsyncValue.guard(
      () => ref.read(calendarServiceProvider).getToday(),
    );
  }
}

final calendarTodayProvider = AsyncNotifierProvider<CalendarTodayNotifier, List<CalendarEvent>>(
  CalendarTodayNotifier.new,
);

class CalendarWeekNotifier extends AsyncNotifier<List<CalendarEvent>> {
  @override
  Future<List<CalendarEvent>> build() async {
    return ref.read(calendarServiceProvider).getWeek();
  }

  Future<void> refresh() async {
    state = const AsyncLoading();
    state = await AsyncValue.guard(
      () => ref.read(calendarServiceProvider).getWeek(),
    );
  }
}

final calendarWeekProvider = AsyncNotifierProvider<CalendarWeekNotifier, List<CalendarEvent>>(
  CalendarWeekNotifier.new,
);
