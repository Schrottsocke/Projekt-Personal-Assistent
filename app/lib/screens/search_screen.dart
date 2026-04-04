import 'dart:async';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:shared_preferences/shared_preferences.dart';
import '../services/search_service.dart';
import '../providers/auth_provider.dart';

final searchServiceProvider = Provider<SearchService>((ref) {
  return SearchService(ref.watch(apiServiceProvider));
});

class SearchScreen extends ConsumerStatefulWidget {
  const SearchScreen({super.key});
  @override
  ConsumerState<SearchScreen> createState() => _SearchScreenState();
}

class _SearchScreenState extends ConsumerState<SearchScreen> {
  final _searchController = TextEditingController();
  Timer? _debounce;
  List<Map<String, dynamic>> _results = [];
  List<String> _history = [];
  bool _loading = false;
  String? _error;

  static const _historyKey = 'search_history';

  @override
  void initState() {
    super.initState();
    _loadHistory();
  }

  @override
  void dispose() {
    _debounce?.cancel();
    _searchController.dispose();
    super.dispose();
  }

  Future<void> _loadHistory() async {
    final prefs = await SharedPreferences.getInstance();
    setState(() {
      _history = prefs.getStringList(_historyKey) ?? [];
    });
  }

  Future<void> _saveHistory(String query) async {
    _history.remove(query);
    _history.insert(0, query);
    if (_history.length > 10) _history = _history.sublist(0, 10);
    final prefs = await SharedPreferences.getInstance();
    await prefs.setStringList(_historyKey, _history);
  }

  void _onSearchChanged(String query) {
    _debounce?.cancel();
    if (query.trim().isEmpty) {
      setState(() {
        _results = [];
        _error = null;
      });
      return;
    }
    _debounce = Timer(const Duration(milliseconds: 300), () {
      _performSearch(query.trim());
    });
  }

  Future<void> _performSearch(String query) async {
    setState(() {
      _loading = true;
      _error = null;
    });
    try {
      final results =
          await ref.read(searchServiceProvider).globalSearch(query);
      await _saveHistory(query);
      if (mounted) {
        setState(() {
          _results = results;
          _loading = false;
        });
      }
    } catch (e) {
      if (mounted) {
        setState(() {
          _error = 'Suche fehlgeschlagen';
          _loading = false;
        });
      }
    }
  }

  IconData _typeIcon(String? type) => switch (type) {
        'task' => Icons.check_box,
        'shopping' => Icons.shopping_cart,
        'recipe' => Icons.restaurant,
        'calendar' => Icons.event,
        'contact' => Icons.person,
        'followup' => Icons.fact_check,
        'document' => Icons.description,
        _ => Icons.article,
      };

  String _typeLabel(String? type) => switch (type) {
        'task' => 'Aufgabe',
        'shopping' => 'Einkauf',
        'recipe' => 'Rezept',
        'calendar' => 'Termin',
        'contact' => 'Kontakt',
        'followup' => 'Follow-up',
        'document' => 'Dokument',
        _ => 'Ergebnis',
      };

  void _navigateToResult(Map<String, dynamic> result) {
    final type = result['type'] as String?;
    final route = switch (type) {
      'task' => '/tasks',
      'shopping' => '/shopping',
      'recipe' => '/recipes',
      'calendar' => '/calendar',
      'followup' => '/followups',
      'document' => '/documents',
      _ => null,
    };
    if (route != null) context.go(route);
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Suche')),
      body: Column(
        children: [
          Padding(
            padding: const EdgeInsets.all(12),
            child: TextField(
              controller: _searchController,
              autofocus: true,
              decoration: InputDecoration(
                hintText: 'Suche nach Aufgaben, Terminen, Kontakten...',
                prefixIcon: const Icon(Icons.search),
                border: const OutlineInputBorder(),
                suffixIcon: _searchController.text.isNotEmpty
                    ? IconButton(
                        icon: const Icon(Icons.clear),
                        onPressed: () {
                          _searchController.clear();
                          setState(() {
                            _results = [];
                            _error = null;
                          });
                        },
                      )
                    : null,
              ),
              onChanged: _onSearchChanged,
            ),
          ),
          if (_loading)
            const LinearProgressIndicator()
          else if (_error != null)
            Padding(
              padding: const EdgeInsets.all(16),
              child: Text(_error!, style: const TextStyle(color: Colors.red)),
            ),
          Expanded(child: _buildBody()),
        ],
      ),
    );
  }

  Widget _buildBody() {
    if (_searchController.text.trim().isEmpty && _history.isNotEmpty) {
      return _buildHistory();
    }
    if (_results.isEmpty && !_loading && _searchController.text.trim().isNotEmpty) {
      return const Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Icon(Icons.search_off, size: 48, color: Colors.grey),
            SizedBox(height: 16),
            Text('Keine Ergebnisse', style: TextStyle(color: Colors.grey)),
          ],
        ),
      );
    }
    if (_results.isEmpty) {
      return const Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Icon(Icons.search, size: 48, color: Colors.grey),
            SizedBox(height: 16),
            Text(
              'Suche nach Aufgaben, Terminen, Kontakten...',
              style: TextStyle(color: Colors.grey),
            ),
          ],
        ),
      );
    }
    return _buildResults();
  }

  Widget _buildHistory() {
    return ListView(
      children: [
        const Padding(
          padding: EdgeInsets.fromLTRB(16, 8, 16, 4),
          child: Text(
            'Letzte Suchen',
            style: TextStyle(fontWeight: FontWeight.bold, color: Colors.grey),
          ),
        ),
        ..._history.map(
          (q) => ListTile(
            leading: const Icon(Icons.history, color: Colors.grey),
            title: Text(q),
            onTap: () {
              _searchController.text = q;
              _searchController.selection = TextSelection.fromPosition(
                TextPosition(offset: q.length),
              );
              _performSearch(q);
            },
          ),
        ),
      ],
    );
  }

  Widget _buildResults() {
    // Group by type
    final grouped = <String, List<Map<String, dynamic>>>{};
    for (final r in _results) {
      final type = r['type'] as String? ?? 'other';
      grouped.putIfAbsent(type, () => []).add(r);
    }

    return ListView(
      children: grouped.entries.expand((entry) {
        return [
          Padding(
            padding: const EdgeInsets.fromLTRB(16, 12, 16, 4),
            child: Row(
              children: [
                Icon(_typeIcon(entry.key), size: 16, color: Colors.grey),
                const SizedBox(width: 8),
                Text(
                  _typeLabel(entry.key),
                  style: const TextStyle(
                    fontWeight: FontWeight.bold,
                    color: Colors.grey,
                  ),
                ),
              ],
            ),
          ),
          ...entry.value.map(
            (r) => ListTile(
              leading: Icon(_typeIcon(entry.key)),
              title: Text(r['title'] as String? ?? ''),
              subtitle: r['subtitle'] != null
                  ? Text(r['subtitle'] as String)
                  : null,
              onTap: () => _navigateToResult(r),
            ),
          ),
        ];
      }).toList(),
    );
  }
}
