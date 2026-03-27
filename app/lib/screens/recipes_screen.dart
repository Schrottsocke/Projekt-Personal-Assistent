import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../models/recipe.dart';
import '../providers/recipe_provider.dart';
import '../providers/auth_provider.dart';
import '../providers/shopping_provider.dart';
import '../services/recipe_service.dart';
import '../widgets/recipe_card.dart';

class RecipesScreen extends ConsumerStatefulWidget {
  const RecipesScreen({super.key});
  @override
  ConsumerState<RecipesScreen> createState() => _RecipesScreenState();
}

class _RecipesScreenState extends ConsumerState<RecipesScreen> with SingleTickerProviderStateMixin {
  late final TabController _tabs;
  final _searchCtrl = TextEditingController();

  @override
  void initState() {
    super.initState();
    _tabs = TabController(length: 2, vsync: this);
  }

  @override
  void dispose() {
    _tabs.dispose();
    _searchCtrl.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Rezepte'),
        bottom: TabBar(controller: _tabs, tabs: const [Tab(text: 'Suche'), Tab(text: 'Gespeichert')]),
      ),
      body: TabBarView(
        controller: _tabs,
        children: [_SearchTab(searchCtrl: _searchCtrl), const _SavedTab()],
      ),
    );
  }
}

class _SearchTab extends ConsumerWidget {
  final TextEditingController searchCtrl;
  const _SearchTab({required this.searchCtrl});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final results = ref.watch(recipeSearchProvider);

    return Column(
      children: [
        Padding(
          padding: const EdgeInsets.all(12),
          child: TextField(
            controller: searchCtrl,
            decoration: InputDecoration(
              hintText: 'Rezept suchen (z.B. Pasta, Suppe)…',
              prefixIcon: const Icon(Icons.search),
              border: const OutlineInputBorder(),
              suffixIcon: searchCtrl.text.isNotEmpty
                  ? IconButton(icon: const Icon(Icons.clear), onPressed: () {
                      searchCtrl.clear();
                      ref.read(recipeSearchQueryProvider.notifier).state = '';
                    })
                  : null,
            ),
            onChanged: (q) => ref.read(recipeSearchQueryProvider.notifier).state = q,
          ),
        ),
        Expanded(child: results.when(
          loading: () => const Center(child: CircularProgressIndicator()),
          error: (e, _) => Center(child: Text('Fehler: $e')),
          data: (recipes) => recipes.isEmpty
              ? Center(child: Text(
                  ref.watch(recipeSearchQueryProvider).isEmpty ? 'Suchbegriff eingeben' : 'Keine Rezepte gefunden',
                  style: const TextStyle(color: Colors.grey),
                ))
              : GridView.builder(
                  padding: const EdgeInsets.all(12),
                  gridDelegate: const SliverGridDelegateWithFixedCrossAxisCount(crossAxisCount: 2, childAspectRatio: 0.75, crossAxisSpacing: 8, mainAxisSpacing: 8),
                  itemCount: recipes.length,
                  itemBuilder: (_, i) => RecipeCard(
                    recipe: recipes[i],
                    onTap: () => _showDetail(context, recipes[i], ref),
                  ),
                ),
        )),
      ],
    );
  }

  void _showDetail(BuildContext context, Recipe recipe, WidgetRef ref) {
    showModalBottomSheet(
      context: context,
      isScrollControlled: true,
      useSafeArea: true,
      builder: (_) => _RecipeDetailSheet(recipe: recipe),
    );
  }
}

class _SavedTab extends ConsumerWidget {
  const _SavedTab();

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final saved = ref.watch(savedRecipesProvider);
    return saved.when(
      loading: () => const Center(child: CircularProgressIndicator()),
      error: (e, _) => Center(child: Text('Fehler: $e')),
      data: (recipes) => recipes.isEmpty
          ? const Center(child: Text('Noch keine gespeicherten Rezepte', style: TextStyle(color: Colors.grey)))
          : GridView.builder(
              padding: const EdgeInsets.all(12),
              gridDelegate: const SliverGridDelegateWithFixedCrossAxisCount(crossAxisCount: 2, childAspectRatio: 0.75, crossAxisSpacing: 8, mainAxisSpacing: 8),
              itemCount: recipes.length,
              itemBuilder: (_, i) => RecipeCard(
                recipe: recipes[i],
                onFavorite: () async {
                  if (recipes[i].savedId != null) {
                    await ref.read(recipeServiceProvider).toggleFavorite(recipes[i].savedId!);
                    ref.invalidate(savedRecipesProvider);
                  }
                },
              ),
            ),
    );
  }
}

class _RecipeDetailSheet extends ConsumerStatefulWidget {
  final Recipe recipe;
  const _RecipeDetailSheet({required this.recipe});
  @override
  ConsumerState<_RecipeDetailSheet> createState() => _RecipeDetailSheetState();
}

class _RecipeDetailSheetState extends ConsumerState<_RecipeDetailSheet> {
  late int _servings;

  @override
  void initState() {
    super.initState();
    _servings = widget.recipe.servings;
  }

  @override
  Widget build(BuildContext context) {
    final r = widget.recipe;
    final scale = _servings / (r.servings == 0 ? 1 : r.servings);

    return DraggableScrollableSheet(
      expand: false,
      initialChildSize: 0.9,
      builder: (_, ctrl) => ListView(
        controller: ctrl,
        children: [
          if (r.imageUrl != null)
            Image.network(r.imageUrl!, height: 200, fit: BoxFit.cover, errorBuilder: (_, __, ___) => const SizedBox.shrink()),
          Padding(
            padding: const EdgeInsets.all(16),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(r.title, style: Theme.of(context).textTheme.titleLarge?.copyWith(fontWeight: FontWeight.bold)),
                const SizedBox(height: 8),
                Row(children: [
                  if (r.timeLabel.isNotEmpty) Chip(label: Text(r.timeLabel)),
                  const SizedBox(width: 8),
                  if (r.difficulty != null) Chip(label: Text(r.difficulty!)),
                ]),
                const SizedBox(height: 16),
                Row(
                  children: [
                    const Text('Portionen:', style: TextStyle(fontWeight: FontWeight.bold)),
                    Expanded(child: Slider(
                      value: _servings.toDouble(),
                      min: 1, max: 12, divisions: 11,
                      label: '$_servings',
                      onChanged: (v) => setState(() => _servings = v.round()),
                    )),
                    Text('$_servings', style: const TextStyle(fontWeight: FontWeight.bold)),
                  ],
                ),
                const SizedBox(height: 8),
                if (r.ingredients.isNotEmpty) ...[
                  const Text('Zutaten', style: TextStyle(fontWeight: FontWeight.bold, fontSize: 16)),
                  const SizedBox(height: 8),
                  ...r.ingredients.map((ing) {
                    final amt = ing['amount'];
                    final scaled = amt is num ? (amt * scale).toStringAsFixed(amt * scale % 1 == 0 ? 0 : 1) : (amt?.toString() ?? '');
                    return Padding(
                      padding: const EdgeInsets.symmetric(vertical: 2),
                      child: Row(children: [
                        SizedBox(width: 60, child: Text('$scaled ${ing['unit'] ?? ''}'.trim(), style: const TextStyle(fontWeight: FontWeight.w500))),
                        const SizedBox(width: 12),
                        Expanded(child: Text(ing['name'] as String? ?? '')),
                      ]),
                    );
                  }),
                ],
                const SizedBox(height: 24),
                Row(children: [
                  Expanded(child: OutlinedButton.icon(
                    onPressed: () async {
                      await ref.read(recipeServiceProvider).toShopping(r.chefkochId, servings: _servings);
                      ref.read(shoppingProvider.notifier).refresh();
                      if (context.mounted) {
                        ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text('Zutaten zur Einkaufsliste hinzugefügt!')));
                        Navigator.pop(context);
                      }
                    },
                    icon: const Icon(Icons.shopping_cart_outlined),
                    label: const Text('Zur Einkaufsliste'),
                  )),
                  const SizedBox(width: 12),
                  Expanded(child: FilledButton.icon(
                    onPressed: () async {
                      await ref.read(recipeServiceProvider).saveRecipe(r);
                      ref.invalidate(savedRecipesProvider);
                      if (context.mounted) {
                        ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text('Rezept gespeichert!')));
                        Navigator.pop(context);
                      }
                    },
                    icon: const Icon(Icons.bookmark_outline),
                    label: const Text('Speichern'),
                  )),
                ]),
              ],
            ),
          ),
        ],
      ),
    );
  }
}
