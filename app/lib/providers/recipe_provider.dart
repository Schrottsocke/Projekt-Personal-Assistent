import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../models/recipe.dart';
import '../services/recipe_service.dart';
import 'auth_provider.dart';

final recipeServiceProvider = Provider<RecipeService>((ref) {
  return RecipeService(ref.watch(apiServiceProvider));
});

final recipeSearchQueryProvider = StateProvider<String>((ref) => '');

final recipeSearchProvider = FutureProvider<List<Recipe>>((ref) async {
  final q = ref.watch(recipeSearchQueryProvider);
  if (q.isEmpty) return [];
  return ref.read(recipeServiceProvider).search(q);
});

final savedRecipesProvider = FutureProvider<List<Recipe>>((ref) async {
  return ref.read(recipeServiceProvider).getSaved();
});
