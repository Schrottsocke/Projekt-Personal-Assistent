import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../services/mobility_service.dart';
import '../providers/auth_provider.dart';

final mobilityServiceProvider = Provider<MobilityService>((ref) {
  return MobilityService(ref.watch(apiServiceProvider));
});

class MobilityScreen extends ConsumerStatefulWidget {
  const MobilityScreen({super.key});
  @override
  ConsumerState<MobilityScreen> createState() => _MobilityScreenState();
}

class _MobilityScreenState extends ConsumerState<MobilityScreen> with SingleTickerProviderStateMixin {
  late TabController _tabController;
  final _originController = TextEditingController();
  final _destController = TextEditingController();
  String _profile = 'driving-car';
  Map<String, dynamic>? _travelResult;
  List<Map<String, dynamic>>? _dailyFlow;
  bool _loadingFlow = false;
  bool _loadingTravel = false;

  static const _profiles = [
    ('driving-car', 'Auto', Icons.directions_car),
    ('cycling-regular', 'Fahrrad', Icons.directions_bike),
    ('foot-walking', 'Zu Fuss', Icons.directions_walk),
  ];

  @override
  void initState() {
    super.initState();
    _tabController = TabController(length: 2, vsync: this);
    _loadDailyFlow();
  }

  @override
  void dispose() {
    _tabController.dispose();
    _originController.dispose();
    _destController.dispose();
    super.dispose();
  }

  Future<void> _loadDailyFlow() async {
    setState(() => _loadingFlow = true);
    try {
      final service = ref.read(mobilityServiceProvider);
      final flow = await service.getDailyFlow();
      setState(() => _dailyFlow = flow);
    } catch (_) {
      // handled by UI
    } finally {
      setState(() => _loadingFlow = false);
    }
  }

  Future<void> _calculateTravel() async {
    final origin = _originController.text.trim();
    final dest = _destController.text.trim();
    if (origin.isEmpty || dest.isEmpty) return;

    setState(() {
      _loadingTravel = true;
      _travelResult = null;
    });
    try {
      final service = ref.read(mobilityServiceProvider);
      final result = await service.getTravelTime(
        origin: origin,
        destination: dest,
        profile: _profile,
      );
      setState(() => _travelResult = result);
    } catch (_) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('Fehler bei der Berechnung')),
        );
      }
    } finally {
      setState(() => _loadingTravel = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final colorScheme = Theme.of(context).colorScheme;

    return Scaffold(
      appBar: AppBar(
        title: const Text('Mobilitaet'),
        bottom: TabBar(
          controller: _tabController,
          tabs: const [
            Tab(text: 'Tagesfluss'),
            Tab(text: 'Fahrzeit-Rechner'),
          ],
        ),
      ),
      body: TabBarView(
        controller: _tabController,
        children: [
          _buildDailyFlow(colorScheme),
          _buildTravelCalculator(colorScheme),
        ],
      ),
    );
  }

  Widget _buildDailyFlow(ColorScheme colorScheme) {
    if (_loadingFlow) {
      return const Center(child: CircularProgressIndicator());
    }

    if (_dailyFlow == null || _dailyFlow!.isEmpty) {
      return Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            const Icon(Icons.timeline, size: 48, color: Colors.grey),
            const SizedBox(height: 16),
            const Text('Kein Tagesfluss verfuegbar', style: TextStyle(color: Colors.grey)),
            const SizedBox(height: 8),
            OutlinedButton(onPressed: _loadDailyFlow, child: const Text('Laden')),
          ],
        ),
      );
    }

    return RefreshIndicator(
      onRefresh: _loadDailyFlow,
      child: ListView.builder(
        padding: const EdgeInsets.all(16),
        itemCount: _dailyFlow!.length,
        itemBuilder: (_, i) {
          final item = _dailyFlow![i];
          final time = item['time'] as String? ?? '';
          final label = item['label'] as String? ?? '';
          final type = item['type'] as String? ?? 'event';

          return Padding(
            padding: const EdgeInsets.symmetric(vertical: 4),
            child: Row(
              children: [
                SizedBox(
                  width: 56,
                  child: Text(time, style: TextStyle(color: colorScheme.primary, fontWeight: FontWeight.bold)),
                ),
                Icon(_typeIcon(type), size: 20, color: Colors.grey),
                const SizedBox(width: 12),
                Expanded(child: Text(label)),
              ],
            ),
          );
        },
      ),
    );
  }

  IconData _typeIcon(String type) {
    return switch (type) {
      'commute' => Icons.directions_car,
      'meeting' => Icons.groups,
      'meal' => Icons.restaurant,
      'sport' => Icons.fitness_center,
      'errand' => Icons.shopping_bag,
      _ => Icons.event,
    };
  }

  Widget _buildTravelCalculator(ColorScheme colorScheme) {
    return SingleChildScrollView(
      padding: const EdgeInsets.all(16),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          TextField(
            controller: _originController,
            decoration: const InputDecoration(
              labelText: 'Start',
              prefixIcon: Icon(Icons.my_location),
              border: OutlineInputBorder(),
            ),
          ),
          const SizedBox(height: 12),
          TextField(
            controller: _destController,
            decoration: const InputDecoration(
              labelText: 'Ziel',
              prefixIcon: Icon(Icons.location_on),
              border: OutlineInputBorder(),
            ),
          ),
          const SizedBox(height: 16),
          SegmentedButton<String>(
            segments: _profiles.map((p) => ButtonSegment(
              value: p.$1,
              label: Text(p.$2),
              icon: Icon(p.$3),
            )).toList(),
            selected: {_profile},
            onSelectionChanged: (v) => setState(() => _profile = v.first),
          ),
          const SizedBox(height: 16),
          FilledButton.icon(
            onPressed: _loadingTravel ? null : _calculateTravel,
            icon: _loadingTravel
                ? const SizedBox(width: 16, height: 16, child: CircularProgressIndicator(strokeWidth: 2))
                : const Icon(Icons.calculate),
            label: const Text('Berechnen'),
          ),
          if (_travelResult != null) ...[
            const SizedBox(height: 24),
            Card(
              child: Padding(
                padding: const EdgeInsets.all(16),
                child: Column(
                  children: [
                    Row(
                      mainAxisAlignment: MainAxisAlignment.center,
                      children: [
                        Icon(Icons.timer, color: colorScheme.primary),
                        const SizedBox(width: 8),
                        Text(
                          _travelResult!['duration_text'] as String? ??
                              '${_travelResult!['duration_minutes'] ?? '?'} Min.',
                          style: const TextStyle(fontSize: 24, fontWeight: FontWeight.bold),
                        ),
                      ],
                    ),
                    const SizedBox(height: 8),
                    Text(
                      _travelResult!['distance_text'] as String? ??
                          '${_travelResult!['distance_km'] ?? '?'} km',
                      style: const TextStyle(color: Colors.grey),
                    ),
                  ],
                ),
              ),
            ),
          ],
        ],
      ),
    );
  }
}
