class MealPlanEntry {
  final int id;
  final String userKey;
  final String plannedDate;
  final String? recipeChefkochId;
  final String recipeTitle;
  final String? recipeImageUrl;
  final String mealType;
  final int servings;
  final String? notes;
  final DateTime createdAt;

  const MealPlanEntry({
    required this.id,
    required this.userKey,
    required this.plannedDate,
    this.recipeChefkochId,
    required this.recipeTitle,
    this.recipeImageUrl,
    required this.mealType,
    required this.servings,
    this.notes,
    required this.createdAt,
  });

  factory MealPlanEntry.fromJson(Map<String, dynamic> j) => MealPlanEntry(
        id: j['id'] as int,
        userKey: j['user_key'] as String,
        plannedDate: j['planned_date'] as String,
        recipeChefkochId: j['recipe_chefkoch_id'] as String?,
        recipeTitle: j['recipe_title'] as String,
        recipeImageUrl: j['recipe_image_url'] as String?,
        mealType: j['meal_type'] as String? ?? 'dinner',
        servings: j['servings'] as int? ?? 4,
        notes: j['notes'] as String?,
        createdAt: DateTime.parse(j['created_at'] as String),
      );

  String get mealTypeLabel => switch (mealType) {
        'breakfast' => 'Frühstück',
        'lunch' => 'Mittagessen',
        _ => 'Abendessen',
      };
}
