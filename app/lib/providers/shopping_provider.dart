import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../models/shopping_item.dart';
import '../services/shopping_service.dart';
import 'auth_provider.dart';

final shoppingServiceProvider = Provider<ShoppingService>((ref) {
  return ShoppingService(ref.watch(apiServiceProvider));
});

class ShoppingNotifier extends AsyncNotifier<List<ShoppingItem>> {
  @override
  Future<List<ShoppingItem>> build() async {
    return ref.read(shoppingServiceProvider).getItems(includeChecked: true);
  }

  Future<void> refresh() async {
    state = const AsyncLoading();
    state = await AsyncValue.guard(
      () => ref.read(shoppingServiceProvider).getItems(includeChecked: true),
    );
  }

  Future<void> addItem(String name, {String? quantity, String? unit}) async {
    await ref.read(shoppingServiceProvider).addItem(name, quantity: quantity, unit: unit);
    await refresh();
  }

  Future<void> toggle(int id) async {
    await ref.read(shoppingServiceProvider).toggleItem(id);
    await refresh();
  }

  Future<void> deleteItem(int id) async {
    await ref.read(shoppingServiceProvider).deleteItem(id);
    await refresh();
  }

  Future<void> clearChecked() async {
    await ref.read(shoppingServiceProvider).clearChecked();
    await refresh();
  }
}

final shoppingProvider = AsyncNotifierProvider<ShoppingNotifier, List<ShoppingItem>>(
  ShoppingNotifier.new,
);
