import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:intl/intl.dart';
import '../models/document.dart';
import '../providers/document_provider.dart';

class DocumentsScreen extends ConsumerStatefulWidget {
  const DocumentsScreen({super.key});
  @override
  ConsumerState<DocumentsScreen> createState() => _DocumentsScreenState();
}

class _DocumentsScreenState extends ConsumerState<DocumentsScreen> {
  String _filter = 'all'; // all, invoice, letter, contract, medical, other

  @override
  Widget build(BuildContext context) {
    final state = ref.watch(documentProvider);

    return Scaffold(
      appBar: AppBar(
        title: const Text('Dokumente'),
        actions: [
          IconButton(
            icon: const Icon(Icons.refresh),
            tooltip: 'Aktualisieren',
            onPressed: () => ref.read(documentProvider.notifier).refresh(),
          ),
        ],
      ),
      body: Column(
        children: [
          _buildFilterChips(),
          Expanded(
            child: state.when(
              loading: () => const Center(child: CircularProgressIndicator()),
              error: (e, _) => Center(
                child: Column(
                  mainAxisAlignment: MainAxisAlignment.center,
                  children: [
                    const Icon(Icons.cloud_off, size: 48, color: Colors.grey),
                    const SizedBox(height: 16),
                    const Text('Dokumente konnten nicht geladen werden'),
                    const SizedBox(height: 8),
                    FilledButton(
                      onPressed: () => ref.invalidate(documentProvider),
                      child: const Text('Erneut versuchen'),
                    ),
                  ],
                ),
              ),
              data: (docs) => _buildList(docs),
            ),
          ),
        ],
      ),
      floatingActionButton: FloatingActionButton(
        onPressed: () => _showUploadPlaceholder(),
        tooltip: 'Dokument hochladen',
        child: const Icon(Icons.camera_alt),
      ),
    );
  }

  Widget _buildFilterChips() {
    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
      child: SingleChildScrollView(
        scrollDirection: Axis.horizontal,
        child: Wrap(
          spacing: 8,
          children: [
            _chip('Alle', 'all'),
            _chip('Rechnungen', 'invoice'),
            _chip('Briefe', 'letter'),
            _chip('Vertraege', 'contract'),
            _chip('Arztbriefe', 'medical'),
            _chip('Sonstiges', 'other'),
          ],
        ),
      ),
    );
  }

  Widget _chip(String label, String value) {
    return FilterChip(
      label: Text(label),
      selected: _filter == value,
      onSelected: (_) => setState(() => _filter = value),
    );
  }

  IconData _docIcon(String type) => switch (type) {
        'invoice' => Icons.receipt_long,
        'letter' => Icons.mail,
        'contract' => Icons.gavel,
        'medical' => Icons.local_hospital,
        _ => Icons.description,
      };

  Widget _buildList(List<ScannedDocument> docs) {
    final filtered = docs.where((d) {
      if (_filter == 'all') return true;
      return d.docType == _filter;
    }).toList();

    if (filtered.isEmpty) {
      return Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            const Icon(Icons.description_outlined, size: 48, color: Colors.grey),
            const SizedBox(height: 16),
            Text(
              _filter == 'all'
                  ? 'Keine Dokumente vorhanden'
                  : 'Keine Dokumente in dieser Kategorie',
              style: const TextStyle(color: Colors.grey),
            ),
          ],
        ),
      );
    }

    final dateFormat = DateFormat('dd.MM.yyyy');

    return RefreshIndicator(
      onRefresh: () async => ref.read(documentProvider.notifier).refresh(),
      child: ListView.builder(
        padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 4),
        itemCount: filtered.length,
        itemBuilder: (_, i) {
          final doc = filtered[i];
          return Card(
            child: ExpansionTile(
              leading: Icon(_docIcon(doc.docType)),
              title: Text(doc.fileName ?? doc.docTypeLabel),
              subtitle: Row(
                children: [
                  Text(doc.docTypeLabel),
                  if (doc.sender != null) ...[
                    const Text(' \u2022 '),
                    Text(doc.sender!),
                  ],
                  if (doc.amount != null) ...[
                    const Text(' \u2022 '),
                    Text('${doc.amount!.toStringAsFixed(2)} \u20ac'),
                  ],
                ],
              ),
              trailing: Text(
                dateFormat.format(doc.createdAt),
                style: const TextStyle(fontSize: 12, color: Colors.grey),
              ),
              children: [
                if (doc.ocrText != null && doc.ocrText!.isNotEmpty)
                  Padding(
                    padding: const EdgeInsets.all(16),
                    child: Text(
                      doc.ocrText!,
                      style: const TextStyle(fontSize: 13),
                    ),
                  ),
                Padding(
                  padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
                  child: Row(
                    children: [
                      OutlinedButton.icon(
                        onPressed: () {
                          ref
                              .read(documentProvider.notifier)
                              .triggerAction(doc.id, 'create_task');
                          ScaffoldMessenger.of(context).showSnackBar(
                            const SnackBar(content: Text('Aufgabe wird erstellt...')),
                          );
                        },
                        icon: const Icon(Icons.check_box_outlined, size: 18),
                        label: const Text('Task erstellen'),
                      ),
                      const SizedBox(width: 8),
                      OutlinedButton.icon(
                        onPressed: () {
                          ref
                              .read(documentProvider.notifier)
                              .triggerAction(doc.id, 'save_memory');
                          ScaffoldMessenger.of(context).showSnackBar(
                            const SnackBar(content: Text('In Memory gespeichert')),
                          );
                        },
                        icon: const Icon(Icons.memory, size: 18),
                        label: const Text('Memory speichern'),
                      ),
                    ],
                  ),
                ),
              ],
            ),
          );
        },
      ),
    );
  }

  void _showUploadPlaceholder() {
    showDialog<void>(
      context: context,
      builder: (_) => AlertDialog(
        title: const Text('Kamera-Upload'),
        content: const Text(
          'Kamera-Upload wird in der naechsten Version unterstuetzt.',
        ),
        actions: [
          FilledButton(
            onPressed: () => Navigator.pop(context),
            child: const Text('OK'),
          ),
        ],
      ),
    );
  }
}
