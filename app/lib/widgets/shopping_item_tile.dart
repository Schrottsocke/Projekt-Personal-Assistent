import 'package:flutter/material.dart';
import '../models/shopping_item.dart';

class ShoppingItemTile extends StatelessWidget {
  final ShoppingItem item;
  final ValueChanged<bool?>? onToggle;
  final VoidCallback? onDelete;

  const ShoppingItemTile({super.key, required this.item, this.onToggle, this.onDelete});

  @override
  Widget build(BuildContext context) {
    return Dismissible(
      key: Key('item_${item.id}'),
      direction: DismissDirection.endToStart,
      onDismissed: (_) => onDelete?.call(),
      background: Container(
        alignment: Alignment.centerRight,
        padding: const EdgeInsets.only(right: 16),
        color: Colors.red.shade700,
        child: const Icon(Icons.delete, color: Colors.white),
      ),
      child: CheckboxListTile(
        value: item.checked,
        onChanged: onToggle,
        title: Text(
          item.name,
          style: TextStyle(
            decoration: item.checked ? TextDecoration.lineThrough : null,
            color: item.checked ? Colors.grey : null,
          ),
        ),
        subtitle: item.displayQuantity.isNotEmpty
            ? Text(item.displayQuantity, style: const TextStyle(fontSize: 12))
            : null,
        secondary: item.category != null
            ? Chip(
                label: Text(item.category!, style: const TextStyle(fontSize: 10)),
                visualDensity: VisualDensity.compact,
              )
            : null,
        dense: true,
      ),
    );
  }
}
