import '../config/api_config.dart';
import '../models/recipe.dart';
import 'api_service.dart';

class RecipeService {
  final ApiService _api;
  RecipeService(this._api);

  Future<List<Recipe>> search(String query, {int limit = 10}) async {
    if (query.isEmpty) return [];
    final resp = await _api.get(
      ApiConfig.recipesSearchPath,
      params: {'q': query, 'limit': limit},
    );
    return (resp.data as List).map((e) => Recipe.fromJson(e as Map<String, dynamic>)).toList();
  }

  Future<Recipe> getRecipe(String chefkochId) async {
    final resp = await _api.get('/recipes/$chefkochId');
    return Recipe.fromJson(resp.data as Map<String, dynamic>);
  }

  Future<List<Recipe>> getSaved() async {
    final resp = await _api.get(ApiConfig.recipesSavedPath);
    return (resp.data as List).map((e) => Recipe.fromJson(e as Map<String, dynamic>)).toList();
  }

  Future<Recipe> saveRecipe(Recipe recipe) async {
    final resp = await _api.post(ApiConfig.recipesSavedPath, data: {
      'chefkoch_id': recipe.chefkochId,
      'title': recipe.title,
      'image_url': recipe.imageUrl,
      'servings': recipe.servings,
      'prep_time': recipe.prepTime,
      'cook_time': recipe.cookTime,
      'difficulty': recipe.difficulty,
      'source_url': recipe.url,
    });
    return Recipe.fromJson(resp.data as Map<String, dynamic>);
  }

  Future<void> deleteSaved(int savedId) async {
    await _api.delete('${ApiConfig.recipesSavedPath}/$savedId');
  }

  Future<void> toggleFavorite(int savedId) async {
    await _api.patch('${ApiConfig.recipesSavedPath}/$savedId/favorite');
  }

  Future<Map<String, dynamic>> toShopping(String chefkochId, {int servings = 4}) async {
    final resp = await _api.post('/recipes/$chefkochId/to-shopping', data: {'servings': servings});
    return resp.data as Map<String, dynamic>;
  }
}
