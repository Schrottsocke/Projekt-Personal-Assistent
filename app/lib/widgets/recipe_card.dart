import 'package:flutter/material.dart';
import 'package:cached_network_image/cached_network_image.dart';
import '../models/recipe.dart';

class RecipeCard extends StatelessWidget {
  final Recipe recipe;
  final VoidCallback? onTap;
  final VoidCallback? onFavorite;

  const RecipeCard({super.key, required this.recipe, this.onTap, this.onFavorite});

  @override
  Widget build(BuildContext context) {
    return Card(
      clipBehavior: Clip.antiAlias,
      child: InkWell(
        onTap: onTap,
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            if (recipe.imageUrl != null)
              CachedNetworkImage(
                imageUrl: recipe.imageUrl!,
                height: 160,
                width: double.infinity,
                fit: BoxFit.cover,
                placeholder: (_, __) => Container(height: 160, color: Colors.grey.shade800),
                errorWidget: (_, __, ___) => Container(
                  height: 160,
                  color: Colors.grey.shade800,
                  child: const Icon(Icons.restaurant, size: 48),
                ),
              ),
            Padding(
              padding: const EdgeInsets.all(12),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(recipe.title, style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 15), maxLines: 2, overflow: TextOverflow.ellipsis),
                  const SizedBox(height: 6),
                  Row(
                    children: [
                      if (recipe.timeLabel.isNotEmpty) ...[
                        const Icon(Icons.timer_outlined, size: 14),
                        const SizedBox(width: 4),
                        Text(recipe.timeLabel, style: const TextStyle(fontSize: 12)),
                        const SizedBox(width: 12),
                      ],
                      if (recipe.difficulty != null) ...[
                        const Icon(Icons.bar_chart, size: 14),
                        const SizedBox(width: 4),
                        Text(recipe.difficulty!, style: const TextStyle(fontSize: 12)),
                      ],
                      const Spacer(),
                      if (onFavorite != null)
                        IconButton(
                          icon: Icon(recipe.isFavorite ? Icons.favorite : Icons.favorite_border, color: Colors.red),
                          onPressed: onFavorite,
                          visualDensity: VisualDensity.compact,
                        ),
                    ],
                  ),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }
}
