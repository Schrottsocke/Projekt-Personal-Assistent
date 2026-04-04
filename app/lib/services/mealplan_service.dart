import '../config/api_config.dart';
import '../models/meal_plan_entry.dart';
import 'api_service.dart';

class MealPlanService {
  final ApiService _api;
  MealPlanService(this._api);

  Future<List<MealPlanEntry>> getWeek(String startDate) async {
    final resp = await _api.get(ApiConfig.mealPlanWeekPath, params: {'start_date': startDate});
    return (resp.data as List).map((e) => MealPlanEntry.fromJson(e as Map<String, dynamic>)).toList();
  }

  Future<MealPlanEntry> create({
    required String date,
    required String mealType,
    required String recipeTitle,
    String? recipeChefkochId,
    int servings = 4,
    String? notes,
  }) async {
    final data = <String, dynamic>{
      'planned_date': date,
      'meal_type': mealType,
      'recipe_title': recipeTitle,
      'servings': servings,
    };
    if (recipeChefkochId != null) data['recipe_chefkoch_id'] = recipeChefkochId;
    if (notes != null) data['notes'] = notes;
    final resp = await _api.post(ApiConfig.mealPlanPath, data: data);
    return MealPlanEntry.fromJson(resp.data as Map<String, dynamic>);
  }

  Future<void> delete(int id) async {
    await _api.delete('${ApiConfig.mealPlanPath}/$id');
  }

  Future<void> weekToShopping(String startDate) async {
    await _api.post('${ApiConfig.mealPlanPath}/week/to-shopping', data: {'start_date': startDate});
  }
}
