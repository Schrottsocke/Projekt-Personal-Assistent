import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../providers/memory_provider.dart';
import '../models/memory_item.dart';

class MemoryScreen extends ConsumerStatefulWidget {
  const MemoryScreen({super.key});
  @override
  ConsumerState<MemoryScreen> createState() => _MemoryScreenState();
}

class _MemoryScreenState extends ConsumerState<MemoryScreen> {
  final _searchController = TextEditingController();

  @override
  void dispose() {
    _searchController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final state = ref.watch(memoryProvider);

    return Scaffold(
      appBar: AppBar(
        title: const Text('Gedaechtnis'),
        actions: [
          IconButton(
            icon: const Icon(Icons.refresh),
            tooltip: 'Aktualisieren',
            onPressed: () {
              _searchController.clear();
              ref.read(memoryProvider.notifier).refresh();
            },
          ),
        ],
      ),
      body: Column(
        children: [
          Padding(
            padding: const EdgeInsets.fromLTRB(16, 8, 16, 4),
            child: TextField(
              controller: _searchController,
              decoration: InputDecoration(
                hintText: 'Erinnerungen durchsuchen...',
                prefixIcon: const Icon(Icons.search),
                border: const OutlineInputBorder(),
                isDense: true,
                contentPadding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
                suffixIcon: _searchController.text.isNotEmpty
                    ? IconButton(
                        icon: const Icon(Icons.clear),
                        onPressed: () {
                          _searchController.clear();
                          ref.read(memoryProvider.notifier).refresh();
                          setState(() {});
                        },
                      )
                    : null,
              ),
              onSubmitted: (q) {
                if (q.trim().isNotEmpty) {
                  ref.read(memoryProvider.notifier).search(q.trim());
                } else {
                  ref.read(memoryProvider.notifier).refresh();
                }
              },
              onChanged: (_) => setState(() {}),
            ),
          ),
          Expanded(
            child: state.when(
              loading: () => const Center(child: CircularProgressIndicator()),
              error: (e, _) => Center(
                child: Column(
                  mainAxisAlignment: MainAxisAlignment.center,
                  children: [
                    const Icon(Icons.cloud_off, size: 48, color: Colors.grey),
                    const SizedBox(height: 16),
                    const Text('Erinnerungen konnten nicht geladen werden'),
                    const SizedBox(height: 8),
                    FilledButton(
                      onPressed: () => ref.invalidate(memoryProvider),
                      child: const Text('Erneut versuchen'),
                    ),
                  ],
                ),
              ),
              data: (memories) {
                if (memories.isEmpty) {
                  return const Center(
                    child: Column(
                      mainAxisAlignment: MainAxisAlignment.center,
                      children: [
                        Icon(Icons.psychology_outlined, size: 48, color: Colors.grey),
                        SizedBox(height: 16),
                        Text('Keine Erinnerungen', style: TextStyle(color: Colors.grey)),
                      ],
                    ),
                  );
                }

                return RefreshIndicator(
                  onRefresh: () async {
                    await ref.read(memoryProvider.notifier).refresh(
                      query: _searchController.text.trim().isNotEmpty
                          ? _searchController.text.trim()
                          : null,
                    );
                  },
                  child: ListView.builder(
                    padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 4),
                    itemCount: memories.length + 1,
                    itemBuilder: (_, i) {
                      if (i == memories.length) {
                        if (memories.length % 20 != 0) return const SizedBox.shrink();
                        return Padding(
                          padding: const EdgeInsets.symmetric(vertical: 16),
                          child: Center(
                            child: OutlinedButton(
                              onPressed: () => ref.read(memoryProvider.notifier).loadMore(
                                query: _searchController.text.trim().isNotEmpty
                                    ? _searchController.text.trim()
                                    : null,
                                offset: memories.length,
                              ),
                              child: const Text('Mehr laden'),
                            ),
                          ),
                        );
                      }
                      return _MemoryCard(
                        item: memories[i],
                        onDelete: () async {
                          final ok = await showDialog<bool>(
                            context: context,
                            builder: (_) => AlertDialog(
                              title: const Text('Erinnerung loeschen?'),
                              content: Text(
                                memories[i].content,
                                maxLines: 3,
                                overflow: TextOverflow.ellipsis,
                              ),
                              actions: [
                                TextButton(onPressed: () => Navigator.pop(context, false), child: const Text('Abbrechen')),
                                FilledButton(onPressed: () => Navigator.pop(context, true), child: const Text('Loeschen')),
                              ],
                            ),
                          );
                          if (ok == true) {
                            await ref.read(memoryProvider.notifier).delete(memories[i].id);
                          }
                        },
                      );
                    },
                  ),
                );
              },
            ),
          ),
        ],
      ),
    );
  }
}

class _MemoryCard extends StatelessWidget {
  final MemoryItem item;
  final VoidCallback onDelete;

  const _MemoryCard({required this.item, required this.onDelete});

  @override
  Widget build(BuildContext context) {
    return Dismissible(
      key: ValueKey(item.id),
      direction: DismissDirection.endToStart,
      confirmDismiss: (_) async {
        onDelete();
        return false;
      },
      background: Container(
        alignment: Alignment.centerRight,
        padding: const EdgeInsets.only(right: 16),
        color: Colors.red,
        child: const Icon(Icons.delete, color: Colors.white),
      ),
      child: Card(
        margin: const EdgeInsets.symmetric(vertical: 4),
        child: Padding(
          padding: const EdgeInsets.all(12),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                item.content,
                maxLines: 4,
                overflow: TextOverflow.ellipsis,
              ),
              if (item.createdAt != null) ...[
                const SizedBox(height: 4),
                Text(
                  '${item.createdAt!.day.toString().padLeft(2, '0')}.${item.createdAt!.month.toString().padLeft(2, '0')}.${item.createdAt!.year}',
                  style: const TextStyle(fontSize: 11, color: Colors.grey),
                ),
              ],
            ],
          ),
        ),
      ),
    );
  }
}
