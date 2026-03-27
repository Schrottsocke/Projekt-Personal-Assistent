import 'package:flutter/material.dart';
import '../models/calendar_event.dart';

class EventCard extends StatelessWidget {
  final CalendarEvent event;
  const EventCard({super.key, required this.event});

  @override
  Widget build(BuildContext context) {
    return Card(
      margin: const EdgeInsets.symmetric(vertical: 4),
      child: ListTile(
        leading: const Icon(Icons.event, color: Colors.blue),
        title: Text(event.summary, maxLines: 1, overflow: TextOverflow.ellipsis),
        subtitle: Text(event.timeLabel),
        trailing: event.location.isNotEmpty
            ? Tooltip(message: event.location, child: const Icon(Icons.place, size: 16))
            : null,
      ),
    );
  }
}
