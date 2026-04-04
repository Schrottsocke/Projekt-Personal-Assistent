import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../models/contact.dart';
import '../providers/contact_provider.dart';

class ContactsScreen extends ConsumerStatefulWidget {
  const ContactsScreen({super.key});
  @override
  ConsumerState<ContactsScreen> createState() => _ContactsScreenState();
}

class _ContactsScreenState extends ConsumerState<ContactsScreen> {
  final _searchController = TextEditingController();

  @override
  void dispose() {
    _searchController.dispose();
    super.dispose();
  }

  void _search() {
    final q = _searchController.text.trim();
    ref.read(contactProvider.notifier).refresh(search: q.isEmpty ? null : q);
  }

  @override
  Widget build(BuildContext context) {
    final state = ref.watch(contactProvider);
    final cs = Theme.of(context).colorScheme;

    return Scaffold(
      appBar: AppBar(
        title: const Text('Kontakte'),
        actions: [
          IconButton(
            icon: const Icon(Icons.refresh),
            tooltip: 'Aktualisieren',
            onPressed: () => ref.read(contactProvider.notifier).refresh(),
          ),
        ],
      ),
      body: Column(
        children: [
          Padding(
            padding: const EdgeInsets.fromLTRB(16, 8, 16, 4),
            child: TextField(
              controller: _searchController,
              decoration: const InputDecoration(
                hintText: 'Kontakte suchen...',
                border: OutlineInputBorder(),
                isDense: true,
                prefixIcon: Icon(Icons.search),
                contentPadding: EdgeInsets.symmetric(horizontal: 12, vertical: 10),
              ),
              onSubmitted: (_) => _search(),
              onChanged: (_) => _search(),
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
                    const Text('Kontakte konnten nicht geladen werden'),
                    const SizedBox(height: 8),
                    FilledButton(
                      onPressed: () => ref.invalidate(contactProvider),
                      child: const Text('Erneut versuchen'),
                    ),
                  ],
                ),
              ),
              data: (contacts) {
                if (contacts.isEmpty) {
                  return const Center(
                    child: Column(
                      mainAxisAlignment: MainAxisAlignment.center,
                      children: [
                        Icon(Icons.contacts_outlined, size: 48, color: Colors.grey),
                        SizedBox(height: 16),
                        Text('Keine Kontakte', style: TextStyle(color: Colors.grey)),
                      ],
                    ),
                  );
                }
                return RefreshIndicator(
                  onRefresh: () async => ref.read(contactProvider.notifier).refresh(),
                  child: ListView.builder(
                    padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 4),
                    itemCount: contacts.length,
                    itemBuilder: (_, i) => _buildContactTile(contacts[i], cs),
                  ),
                );
              },
            ),
          ),
        ],
      ),
      floatingActionButton: FloatingActionButton(
        onPressed: () => _showContactDialog(context),
        tooltip: 'Neuer Kontakt',
        child: const Icon(Icons.person_add),
      ),
    );
  }

  Widget _buildContactTile(Contact contact, ColorScheme cs) {
    final initials = contact.name.isNotEmpty ? contact.name[0].toUpperCase() : '?';
    final subtitle = contact.email ?? contact.phone ?? '';

    return Card(
      child: ListTile(
        leading: CircleAvatar(
          backgroundColor: cs.primaryContainer,
          child: Text(initials, style: TextStyle(color: cs.onPrimaryContainer)),
        ),
        title: Text(contact.name),
        subtitle: subtitle.isNotEmpty ? Text(subtitle) : null,
        trailing: contact.tags.isNotEmpty
            ? Wrap(
                spacing: 4,
                children: contact.tags
                    .take(2)
                    .map((t) => Chip(
                          label: Text(t, style: const TextStyle(fontSize: 10)),
                          materialTapTargetSize: MaterialTapTargetSize.shrinkWrap,
                          visualDensity: VisualDensity.compact,
                          padding: EdgeInsets.zero,
                        ))
                    .toList(),
              )
            : null,
        onTap: () => _showDetailDialog(contact),
        onLongPress: () => _confirmDelete(contact),
      ),
    );
  }

  void _showDetailDialog(Contact contact) {
    showDialog(
      context: context,
      builder: (ctx) => AlertDialog(
        title: Text(contact.name),
        content: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            if (contact.email != null) ...[
              Row(children: [
                const Icon(Icons.email_outlined, size: 18),
                const SizedBox(width: 8),
                Flexible(child: Text(contact.email!)),
              ]),
              const SizedBox(height: 8),
            ],
            if (contact.phone != null) ...[
              Row(children: [
                const Icon(Icons.phone_outlined, size: 18),
                const SizedBox(width: 8),
                Text(contact.phone!),
              ]),
              const SizedBox(height: 8),
            ],
            if (contact.notes != null && contact.notes!.isNotEmpty) ...[
              Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
                const Icon(Icons.notes_outlined, size: 18),
                const SizedBox(width: 8),
                Flexible(child: Text(contact.notes!)),
              ]),
              const SizedBox(height: 8),
            ],
            if (contact.tags.isNotEmpty) ...[
              Wrap(
                spacing: 4,
                runSpacing: 4,
                children: contact.tags
                    .map((t) => Chip(label: Text(t, style: const TextStyle(fontSize: 12))))
                    .toList(),
              ),
              const SizedBox(height: 8),
            ],
            if (contact.source != null)
              Text('Quelle: ${contact.source}', style: const TextStyle(color: Colors.grey, fontSize: 12)),
          ],
        ),
        actions: [
          TextButton(
            onPressed: () {
              Navigator.pop(ctx);
              _showContactDialog(context, contact: contact);
            },
            child: const Text('Bearbeiten'),
          ),
          TextButton(
            onPressed: () => Navigator.pop(ctx),
            child: const Text('Schliessen'),
          ),
        ],
      ),
    );
  }

  void _showContactDialog(BuildContext context, {Contact? contact}) {
    final nameCtrl = TextEditingController(text: contact?.name ?? '');
    final emailCtrl = TextEditingController(text: contact?.email ?? '');
    final phoneCtrl = TextEditingController(text: contact?.phone ?? '');
    final notesCtrl = TextEditingController(text: contact?.notes ?? '');
    final tagsCtrl = TextEditingController(text: contact?.tags.join(', ') ?? '');
    final isEdit = contact != null;

    showDialog(
      context: context,
      builder: (ctx) => AlertDialog(
        title: Text(isEdit ? 'Kontakt bearbeiten' : 'Neuer Kontakt'),
        content: SingleChildScrollView(
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              TextField(
                controller: nameCtrl,
                decoration: const InputDecoration(labelText: 'Name *', border: OutlineInputBorder()),
              ),
              const SizedBox(height: 12),
              TextField(
                controller: emailCtrl,
                decoration: const InputDecoration(labelText: 'E-Mail', border: OutlineInputBorder()),
                keyboardType: TextInputType.emailAddress,
              ),
              const SizedBox(height: 12),
              TextField(
                controller: phoneCtrl,
                decoration: const InputDecoration(labelText: 'Telefon', border: OutlineInputBorder()),
                keyboardType: TextInputType.phone,
              ),
              const SizedBox(height: 12),
              TextField(
                controller: notesCtrl,
                decoration: const InputDecoration(labelText: 'Notizen', border: OutlineInputBorder()),
                maxLines: 3,
              ),
              const SizedBox(height: 12),
              TextField(
                controller: tagsCtrl,
                decoration: const InputDecoration(
                  labelText: 'Tags (kommagetrennt)',
                  border: OutlineInputBorder(),
                ),
              ),
            ],
          ),
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(ctx),
            child: const Text('Abbrechen'),
          ),
          FilledButton(
            onPressed: () {
              final name = nameCtrl.text.trim();
              if (name.isEmpty) return;
              Navigator.pop(ctx);

              final tags = tagsCtrl.text
                  .split(',')
                  .map((t) => t.trim())
                  .where((t) => t.isNotEmpty)
                  .toList();
              final email = emailCtrl.text.trim();
              final phone = phoneCtrl.text.trim();
              final notes = notesCtrl.text.trim();

              if (isEdit) {
                ref.read(contactProvider.notifier).updateContact(
                      contact.id,
                      name: name,
                      email: email.isEmpty ? null : email,
                      phone: phone.isEmpty ? null : phone,
                      notes: notes.isEmpty ? null : notes,
                      tags: tags,
                    );
              } else {
                ref.read(contactProvider.notifier).addContact(
                      name: name,
                      email: email.isEmpty ? null : email,
                      phone: phone.isEmpty ? null : phone,
                      notes: notes.isEmpty ? null : notes,
                      tags: tags,
                    );
              }
            },
            child: Text(isEdit ? 'Speichern' : 'Erstellen'),
          ),
        ],
      ),
    );
  }

  void _confirmDelete(Contact contact) {
    showDialog(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text('Kontakt loeschen?'),
        content: Text('${contact.name} wirklich loeschen?'),
        actions: [
          TextButton(onPressed: () => Navigator.pop(ctx), child: const Text('Abbrechen')),
          FilledButton(
            onPressed: () {
              Navigator.pop(ctx);
              ref.read(contactProvider.notifier).deleteContact(contact.id);
            },
            child: const Text('Loeschen'),
          ),
        ],
      ),
    );
  }
}
