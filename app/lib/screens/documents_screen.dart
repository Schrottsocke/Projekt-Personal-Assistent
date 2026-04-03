import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

class DocumentsScreen extends ConsumerStatefulWidget {
  const DocumentsScreen({super.key});
  @override
  ConsumerState<DocumentsScreen> createState() => _DocumentsScreenState();
}

class _DocumentsScreenState extends ConsumerState<DocumentsScreen> {
  bool _loading = false;
  List<Map<String, dynamic>> _documents = [];

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    setState(() => _loading = true);
    try {
      // TODO: API-Call ueber Provider implementieren
      _documents = [];
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
        title: const Text('Dokumente'),
        actions: [
          IconButton(
            icon: const Icon(Icons.refresh),
            onPressed: _load,
          ),
        ],
      ),
      floatingActionButton: FloatingActionButton(
        onPressed: () {
          // TODO: Dokument-Upload implementieren
        },
        child: const Icon(Icons.upload_file),
      ),
      body: _loading
          ? const Center(child: CircularProgressIndicator())
          : _documents.isEmpty
              ? Center(
                  child: Column(
                    mainAxisAlignment: MainAxisAlignment.center,
                    children: [
                      Icon(Icons.scanner, size: 64, color: Colors.grey.shade600),
                      const SizedBox(height: 16),
                      const Text('Keine Dokumente vorhanden'),
                      const SizedBox(height: 8),
                      Text(
                        'Lade ein Dokument hoch, um OCR und Analyse zu starten.',
                        style: TextStyle(color: Colors.grey.shade500, fontSize: 13),
                      ),
                    ],
                  ),
                )
              : RefreshIndicator(
                  onRefresh: _load,
                  child: ListView.builder(
                    padding: const EdgeInsets.all(16),
                    itemCount: _documents.length,
                    itemBuilder: (context, index) {
                      final doc = _documents[index];
                      return Card(
                        margin: const EdgeInsets.only(bottom: 8),
                        child: ListTile(
                          leading: const Icon(Icons.description),
                          title: Text(doc['doc_type'] ?? 'Dokument'),
                          subtitle: Text(doc['summary'] ?? doc['filename'] ?? ''),
                          trailing: doc['amount'] != null
                              ? Text(doc['amount'], style: const TextStyle(fontWeight: FontWeight.bold))
                              : null,
                        ),
                      );
                    },
                  ),
                ),
    );
  }
}
