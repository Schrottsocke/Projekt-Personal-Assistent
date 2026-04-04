import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../models/meal_plan_entry.dart';
import '../services/mealplan_service.dart';
import 'auth_provider.dart';

final mealplanServiceProvider = Provider<MealPlanService>((ref) {
  return MealPlanService(ref.watch(apiServiceProvider));
});

/// Returns the Monday of the current week as yyyy-MM-dd.
String _currentMonday() {
  final now = DateTime.now();
  final monday = now.subtract(Duration(days: now.weekday - 1));
  return '${monday.year}-${monday.month.toString().padLeft(2, '0')}-${monday.day.toString().padLeft(2, '0')}';
}

class MealPlanNotifier extends AsyncNotifier<List<MealPlanEntry>> {
  String _weekStart = _currentMonday();

  String get weekStart => _weekStart;

  @override
  Future<List<MealPlanEntry>> build() async {
    return ref.read(mealplanServiceProvider).getWeek(_weekStart);
  }

  Future<void> refresh() async {
    state = const AsyncLoading();
    state = await AsyncValue.guard(
      () => ref.read(mealplanServiceProvider).getWeek(_weekStart),
    );
  }

  Future<void> setWeek(String startDate) async {
    _weekStart = startDate;
    await refresh();
  }

  Future<void> previousWeek() async {
    final current = DateTime.parse(_weekStart);
    final prev = current.subtract(const Duration(days: 7));
    await setWeek('${prev.year}-${prev.month.toString().padLeft(2, '0')}-${prev.day.toString().padLeft(2, '0')}');
  }

  Future<void> nextWeek() async {
    final current = DateTime.parse(_weekStart);
    final next = current.add(const Duration(days: 7));
    await setWeek('${next.year}-${next.month.toString().padLeft(2, '0')}-${next.day.toString().padLeft(2, '0')}');
  }

  Future<void> addEntry({
    required String date,
    required String mealType,
    required String recipeTitle,
    String? recipeChefkochId,
    int servings = 4,
    String? notes,
  }) async {
    await ref.read(mealplanServiceProvider).create(
      date: date,
      mealType: mealType,
      recipeTitle: recipeTitle,
      recipeChefkochId: recipeChefkochId,
      servings: servings,
      notes: notes,
    );
    await refresh();
  }

  Future<void> deleteEntry(int id) async {
    await ref.read(mealplanServiceProvider).delete(id);
    await refresh();
  }

  Future<void> exportToShopping() async {
    await ref.read(mealplanServiceProvider).weekToShopping(_weekStart);
  }
}

final mealplanProvider = AsyncNotifierProvider<MealPlanNotifier, List<MealPlanEntry>>(
  MealPlanNotifier.new,
);
