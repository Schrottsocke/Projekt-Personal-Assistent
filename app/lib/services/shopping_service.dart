import '../config/api_config.dart';
import '../models/shopping_item.dart';
import 'api_service.dart';

class ShoppingService {
  final ApiService _api;
  ShoppingService(this._api);

  Future<List<ShoppingItem>> getItems({bool includeChecked = false}) async {
    final resp = await _api.get(
      ApiConfig.shoppingItemsPath,
      params: {'include_checked': includeChecked},
    );
    return (resp.data as List).map((e) => ShoppingItem.fromJson(e as Map<String, dynamic>)).toList();
  }

  Future<ShoppingItem> addItem(String name, {String? quantity, String? unit, String? category}) async {
    final resp = await _api.post(ApiConfig.shoppingItemsPath, data: {
      'name': name,
      if (quantity != null) 'quantity': quantity,
      if (unit != null) 'unit': unit,
      if (category != null) 'category': category,
    });
    return ShoppingItem.fromJson(resp.data as Map<String, dynamic>);
  }

  Future<void> toggleItem(int id) async {
    await _api.patch('${ApiConfig.shoppingItemsPath}/$id', data: {'checked': true});
  }

  Future<void> deleteItem(int id) async {
    await _api.delete('${ApiConfig.shoppingItemsPath}/$id');
  }

  Future<void> clearChecked() async {
    await _api.delete('${ApiConfig.shoppingItemsPath}/checked');
  }

  Future<Map<String, dynamic>> addFromRecipe(String chefkochId, {int servings = 4}) async {
    final resp = await _api.post(
      '${ApiConfig.shoppingFromRecipePath}/$chefkochId',
      data: {'servings': servings},
    );
    return resp.data as Map<String, dynamic>;
  }
}
