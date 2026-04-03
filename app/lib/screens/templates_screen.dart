import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

class TemplatesScreen extends ConsumerStatefulWidget {
  const TemplatesScreen({super.key});
  @override
  ConsumerState<TemplatesScreen> createState() => _TemplatesScreenState();
}

class _TemplatesScreenState extends ConsumerState<TemplatesScreen> {
  bool _loading = false;
  List<Map<String, dynamic>> _templates = [];
  String? _categoryFilter;

  static const _categories = {
    'shopping': ('Einkauf', Icons.shopping_cart),
    'message': ('Nachricht', Icons.chat_bubble),
    'task': ('Aufgabe', Icons.check_circle),
    'routine': ('Routine', Icons.repeat),
    'checklist': ('Checkliste', Icons.checklist),
  };

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    setState(() => _loading = true);
    try {
      // TODO: API-Call ueber Provider implementieren
      _templates = [];
    } catch (_) {
      // Fehlerbehandlung
    } finally {
      setState(() => _loading = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Vorlagen'),
        actions: [
          IconButton(
            icon: const Icon(Icons.refresh),
            onPressed: _load,
          ),
        ],
      ),
      floatingActionButton: FloatingActionButton(
        onPressed: () {
          // TODO: Vorlage erstellen
        },
        child: const Icon(Icons.add),
      ),
      body: Column(
        children: [
          // Kategorie-Filter
          SizedBox(
            height: 48,
            child: ListView(
              scrollDirection: Axis.horizontal,
              padding: const EdgeInsets.symmetric(horizontal: 12),
              children: [
                Padding(
                  padding: const EdgeInsets.symmetric(horizontal: 4),
                  child: FilterChip(
                    label: const Text('Alle'),
                    selected: _categoryFilter == null,
                    onSelected: (_) => setState(() {
                      _categoryFilter = null;
                      _load();
                    }),
                  ),
                ),
                ..._categories.entries.map((e) => Padding(
                  padding: const EdgeInsets.symmetric(horizontal: 4),
                  child: FilterChip(
                    label: Text(e.value.$1),
                    avatar: Icon(e.value.$2, size: 16),
                    selected: _categoryFilter == e.key,
                    onSelected: (_) => setState(() {
                      _categoryFilter = e.key;
                      _load();
                    }),
                  ),
                )),
              ],
            ),
          ),
          // Liste
          Expanded(
            child: _loading
                ? const Center(child: CircularProgressIndicator())
                : _templates.isEmpty
                    ? Center(
                        child: Column(
                          mainAxisAlignment: MainAxisAlignment.center,
                          children: [
                            Icon(Icons.library_books, size: 64, color: Colors.grey.shade600),
                            const SizedBox(height: 16),
                            const Text('Keine Vorlagen vorhanden'),
                            const SizedBox(height: 8),
                            Text(
                              'Erstelle Vorlagen fuer haeufig genutzte Inhalte.',
                              style: TextStyle(color: Colors.grey.shade500, fontSize: 13),
                            ),
                          ],
                        ),
                      )
                    : RefreshIndicator(
                        onRefresh: _load,
                        child: ListView.builder(
                          padding: const EdgeInsets.all(16),
                          itemCount: _templates.length,
                          itemBuilder: (context, index) {
                            final tpl = _templates[index];
                            final cat = _categories[tpl['category']];
                            return Card(
                              margin: const EdgeInsets.only(bottom: 8),
                              child: ListTile(
                                leading: Icon(cat?.$2 ?? Icons.article),
                                title: Text(tpl['name'] ?? 'Vorlage'),
                                subtitle: Text(tpl['description'] ?? ''),
                                trailing: Row(
                                  mainAxisSize: MainAxisSize.min,
                                  children: [
                                    if (tpl['use_count'] != null && tpl['use_count'] > 0)
                                      Text('${tpl['use_count']}x',
                                          style: TextStyle(color: Colors.grey.shade500, fontSize: 12)),
                                    IconButton(
                                      icon: const Icon(Icons.play_arrow),
                                      onPressed: () {
                                        // TODO: Vorlage anwenden
                                      },
                                    ),
                                  ],
                                ),
                              ),
                            );
                          },
                        ),
                      ),
          ),
        ],
      ),
    );
  }
}
