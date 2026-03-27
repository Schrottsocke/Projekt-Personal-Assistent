class ShoppingItem {
  final int id;
  final String name;
  final String? quantity;
  final String? unit;
  final String? category;
  final bool checked;
  final String? source;
  final DateTime createdAt;

  const ShoppingItem({
    required this.id,
    required this.name,
    this.quantity,
    this.unit,
    this.category,
    required this.checked,
    this.source,
    required this.createdAt,
  });

  factory ShoppingItem.fromJson(Map<String, dynamic> j) => ShoppingItem(
        id: j['id'] as int,
        name: j['name'] as String,
        quantity: j['quantity'] as String?,
        unit: j['unit'] as String?,
        category: j['category'] as String?,
        checked: j['checked'] as bool? ?? false,
        source: j['source'] as String?,
        createdAt: DateTime.parse(j['created_at'] as String),
      );

  ShoppingItem copyWith({bool? checked}) => ShoppingItem(
        id: id,
        name: name,
        quantity: quantity,
        unit: unit,
        category: category,
        checked: checked ?? this.checked,
        source: source,
        createdAt: createdAt,
      );

  String get displayQuantity {
    if (quantity == null && unit == null) return '';
    return [quantity, unit].where((s) => s != null && s.isNotEmpty).join(' ');
  }
}
