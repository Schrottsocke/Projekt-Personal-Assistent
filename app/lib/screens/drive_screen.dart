import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../services/drive_service.dart';
import '../providers/auth_provider.dart';

final driveServiceProvider = Provider<DriveService>((ref) {
  return DriveService(ref.watch(apiServiceProvider));
});

final driveFilesProvider = FutureProvider.family<List<Map<String, dynamic>>, String?>((ref, query) {
  return ref.read(driveServiceProvider).listFiles(query: query);
});

class DriveScreen extends ConsumerStatefulWidget {
  const DriveScreen({super.key});
  @override
  ConsumerState<DriveScreen> createState() => _DriveScreenState();
}

class _DriveScreenState extends ConsumerState<DriveScreen> {
  final _searchController = TextEditingController();
  String? _query;

  @override
  void dispose() {
    _searchController.dispose();
    super.dispose();
  }

  void _search() {
    final q = _searchController.text.trim();
    setState(() => _query = q.isEmpty ? null : q);
  }

  IconData _mimeIcon(String? mimeType) {
    final m = (mimeType ?? '').toLowerCase();
    if (m.contains('pdf')) return Icons.picture_as_pdf;
    if (m.contains('image')) return Icons.image;
    if (m.contains('spreadsheet') || m.contains('excel')) return Icons.table_chart;
    if (m.contains('document') || m.contains('word') || m.contains('text')) return Icons.description;
    if (m.contains('folder')) return Icons.folder;
    if (m.contains('presentation') || m.contains('powerpoint')) return Icons.slideshow;
    if (m.contains('video')) return Icons.videocam;
    if (m.contains('audio')) return Icons.audiotrack;
    return Icons.insert_drive_file;
  }

  String _formatSize(dynamic size) {
    if (size == null) return '';
    final bytes = size is int ? size : int.tryParse(size.toString()) ?? 0;
    if (bytes < 1024) return '$bytes B';
    if (bytes < 1024 * 1024) return '${(bytes / 1024).toStringAsFixed(1)} KB';
    if (bytes < 1024 * 1024 * 1024) return '${(bytes / (1024 * 1024)).toStringAsFixed(1)} MB';
    return '${(bytes / (1024 * 1024 * 1024)).toStringAsFixed(1)} GB';
  }

  @override
  Widget build(BuildContext context) {
    final files = ref.watch(driveFilesProvider(_query));
    final cs = Theme.of(context).colorScheme;

    return Scaffold(
      appBar: AppBar(title: const Text('Drive')),
      body: Column(
        children: [
          Padding(
            padding: const EdgeInsets.fromLTRB(16, 8, 16, 4),
            child: Row(
              children: [
                Expanded(
                  child: TextField(
                    controller: _searchController,
                    decoration: const InputDecoration(
                      hintText: 'Dateien suchen...',
                      border: OutlineInputBorder(),
                      isDense: true,
                      prefixIcon: Icon(Icons.search),
                      contentPadding: EdgeInsets.symmetric(horizontal: 12, vertical: 10),
                    ),
                    onSubmitted: (_) => _search(),
                  ),
                ),
                const SizedBox(width: 8),
                FilledButton(
                  onPressed: _search,
                  child: const Icon(Icons.search),
                ),
              ],
            ),
          ),
          Expanded(
            child: files.when(
              loading: () => const Center(child: CircularProgressIndicator()),
              error: (e, _) => Center(
                child: Column(
                  mainAxisAlignment: MainAxisAlignment.center,
                  children: [
                    const Icon(Icons.cloud_off, size: 48, color: Colors.grey),
                    const SizedBox(height: 16),
                    const Text('Dateien konnten nicht geladen werden'),
                    const SizedBox(height: 8),
                    FilledButton(
                      onPressed: () => ref.invalidate(driveFilesProvider),
                      child: const Text('Erneut versuchen'),
                    ),
                  ],
                ),
              ),
              data: (fileList) {
                if (fileList.isEmpty) {
                  return const Center(
                    child: Column(
                      mainAxisAlignment: MainAxisAlignment.center,
                      children: [
                        Icon(Icons.folder_open, size: 48, color: Colors.grey),
                        SizedBox(height: 16),
                        Text('Keine Dateien gefunden', style: TextStyle(color: Colors.grey)),
                      ],
                    ),
                  );
                }
                return RefreshIndicator(
                  onRefresh: () async => ref.invalidate(driveFilesProvider),
                  child: ListView.builder(
                    padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 4),
                    itemCount: fileList.length,
                    itemBuilder: (_, i) {
                      final file = fileList[i];
                      final name = file['name'] ?? file['title'] ?? 'Unbekannt';
                      final mime = file['mime_type'] ?? file['mimeType'] ?? '';
                      final size = file['size'];
                      final modified = file['modified_at'] ?? file['modifiedTime'] ?? '';

                      return Card(
                        child: ListTile(
                          leading: Icon(_mimeIcon(mime.toString()), color: cs.primary),
                          title: Text(name.toString(), maxLines: 1, overflow: TextOverflow.ellipsis),
                          subtitle: Text(
                            [
                              if (size != null) _formatSize(size),
                              if (modified.toString().isNotEmpty) modified.toString(),
                            ].join(' \u2022 '),
                            maxLines: 1,
                            overflow: TextOverflow.ellipsis,
                          ),
                        ),
                      );
                    },
                  ),
                );
              },
            ),
          ),
        ],
      ),
      floatingActionButton: FloatingActionButton(
        onPressed: () {
          ScaffoldMessenger.of(context).showSnackBar(
            const SnackBar(content: Text('Datei-Upload kommt bald')),
          );
        },
        tooltip: 'Hochladen',
        child: const Icon(Icons.upload_file),
      ),
    );
  }
}
