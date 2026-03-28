import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../providers/shopping_provider.dart';
import '../models/shopping_item.dart';
import '../widgets/shopping_item_tile.dart';

class ShoppingScreen extends ConsumerStatefulWidget {
  const ShoppingScreen({super.key});
  @override
  ConsumerState<ShoppingScreen> createState() => _ShoppingScreenState();
}

class _ShoppingScreenState extends ConsumerState<ShoppingScreen> {
  final _addController = TextEditingController();
  bool _showChecked = true;

  @override
  void dispose() {
    _addController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final state = ref.watch(shoppingProvider);

    return Scaffold(
      appBar: AppBar(
        title: const Text('Einkaufsliste'),
        actions: [
          IconButton(
            icon: Icon(_showChecked ? Icons.visibility : Icons.visibility_off),
            tooltip: _showChecked ? 'Abgehakte ausblenden' : 'Alle anzeigen',
            onPressed: () => setState(() => _showChecked = !_showChecked),
          ),
          IconButton(
            icon: const Icon(Icons.delete_sweep),
            tooltip: 'Abgehakte löschen',
            onPressed: () async {
              final ok = await showDialog<bool>(context: context, builder: (_) => AlertDialog(
                title: const Text('Abgehakte löschen?'),
                actions: [
                  TextButton(onPressed: () => Navigator.pop(context, false), child: const Text('Abbrechen')),
                  FilledButton(onPressed: () => Navigator.pop(context, true), child: const Text('Löschen')),
                ],
              ));
              if (ok == true) ref.read(shoppingProvider.notifier).clearChecked();
            },
          ),
        ],
      ),
      body: Column(
        children: [
          _buildProgress(state.value ?? []),
          _buildAddField(),
          Expanded(child: state.when(
            loading: () => const Center(child: CircularProgressIndicator()),
            error: (e, _) => Center(child: Column(
              mainAxisAlignment: MainAxisAlignment.center,
              children: [
                const Icon(Icons.cloud_off, size: 48, color: Colors.grey),
                const SizedBox(height: 16),
                const Text('Daten konnten nicht geladen werden'),
                const SizedBox(height: 8),
                FilledButton(
                  onPressed: () => ref.invalidate(shoppingProvider),
                  child: const Text('Erneut versuchen'),
                ),
              ],
            )),
            data: (items) => _buildList(items),
          )),
        ],
      ),
    );
  }

  Widget _buildProgress(List<ShoppingItem> items) {
    final total = items.length;
    final checked = items.where((i) => i.checked).length;
    if (total == 0) return const SizedBox.shrink();
    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 4),
      child: Column(
        children: [
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Text('$checked von $total erledigt', style: const TextStyle(fontSize: 12, color: Colors.grey)),
              Text('${total > 0 ? ((checked / total) * 100).round() : 0}%', style: const TextStyle(fontSize: 12, color: Colors.grey)),
            ],
          ),
          const SizedBox(height: 4),
          LinearProgressIndicator(value: total > 0 ? checked / total : 0, backgroundColor: Colors.grey.shade800),
        ],
      ),
    );
  }

  Widget _buildAddField() {
    return Padding(
      padding: const EdgeInsets.fromLTRB(16, 8, 16, 4),
      child: Row(
        children: [
          Expanded(
            child: TextField(
              controller: _addController,
              decoration: const InputDecoration(hintText: 'Artikel hinzufügen…', border: OutlineInputBorder(), isDense: true, contentPadding: EdgeInsets.symmetric(horizontal: 12, vertical: 10)),
              onSubmitted: (_) => _addItem(),
            ),
          ),
          const SizedBox(width: 8),
          FilledButton(onPressed: _addItem, child: const Icon(Icons.add)),
        ],
      ),
    );
  }

  Future<void> _addItem() async {
    final name = _addController.text.trim();
    if (name.isEmpty) return;
    _addController.clear();
    await ref.read(shoppingProvider.notifier).addItem(name);
  }

  Widget _buildList(List<ShoppingItem> items) {
    final Map<String, List<ShoppingItem>> grouped = {};
    for (final item in items) {
      if (!_showChecked && item.checked) continue;
      final cat = item.category ?? 'Sonstiges';
      grouped.putIfAbsent(cat, () => []).add(item);
    }

    if (grouped.isEmpty) {
      return Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: const [
            Icon(Icons.shopping_cart_outlined, size: 48, color: Colors.grey),
            SizedBox(height: 16),
            Text('Einkaufsliste ist leer', style: TextStyle(color: Colors.grey)),
          ],
        ),
      );
    }

    return ListView(
      children: grouped.entries.map((entry) => Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Padding(
            padding: const EdgeInsets.fromLTRB(16, 12, 16, 4),
            child: Text(entry.key, style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 13, color: Colors.grey)),
          ),
          ...entry.value.map((item) => ShoppingItemTile(
            item: item,
            onToggle: (_) => ref.read(shoppingProvider.notifier).toggle(item.id),
            onDelete: () => ref.read(shoppingProvider.notifier).deleteItem(item.id),
          )),
        ],
      )).toList(),
    );
  }
}
