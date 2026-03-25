class Recipe {
  final String chefkochId;
  final String title;
  final String? imageUrl;
  final int prepTime;
  final int cookTime;
  final String? difficulty;
  final double rating;
  final String url;
  final int servings;
  final List<Map<String, dynamic>> ingredients;
  bool isFavorite;
  int? savedId;

  Recipe({
    required this.chefkochId,
    required this.title,
    this.imageUrl,
    this.prepTime = 0,
    this.cookTime = 0,
    this.difficulty,
    this.rating = 0.0,
    required this.url,
    this.servings = 4,
    this.ingredients = const [],
    this.isFavorite = false,
    this.savedId,
  });

  factory Recipe.fromJson(Map<String, dynamic> j) => Recipe(
        chefkochId: j['chefkoch_id'] as String? ?? j['id']?.toString() ?? '',
        title: j['title'] as String? ?? '',
        imageUrl: j['image_url'] as String?,
        prepTime: j['prep_time'] as int? ?? 0,
        cookTime: j['cook_time'] as int? ?? 0,
        difficulty: j['difficulty'] as String?,
        rating: (j['rating'] as num?)?.toDouble() ?? 0.0,
        url: j['url'] as String? ?? '',
        servings: j['servings'] as int? ?? 4,
        ingredients: (j['ingredients'] as List<dynamic>?)
                ?.map((e) => Map<String, dynamic>.from(e as Map))
                .toList() ??
            [],
        isFavorite: j['is_favorite'] as bool? ?? false,
        savedId: j['id'] as int?,
      );

  String get timeLabel {
    final total = prepTime + cookTime;
    if (total == 0) return '';
    if (total < 60) return '${total} Min.';
    return '${total ~/ 60}h ${total % 60}min';
  }
}
