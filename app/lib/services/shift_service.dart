import '../config/api_config.dart';
import '../models/shift.dart';
import 'api_service.dart';

class ShiftService {
  final ApiService _api;
  ShiftService(this._api);

  Future<List<ShiftType>> getTypes() async {
    final resp = await _api.get(ApiConfig.shiftTypesPath);
    return (resp.data as List).map((e) => ShiftType.fromJson(e as Map<String, dynamic>)).toList();
  }

  Future<ShiftType> createType({
    required String name,
    required String color,
    required String category,
  }) async {
    final resp = await _api.post(ApiConfig.shiftTypesPath, data: {
      'name': name,
      'color': color,
      'category': category,
    });
    return ShiftType.fromJson(resp.data as Map<String, dynamic>);
  }

  Future<void> deleteType(int id) async {
    await _api.delete('${ApiConfig.shiftTypesPath}/$id');
  }

  Future<List<ShiftEntry>> getEntries(String month) async {
    final resp = await _api.get(ApiConfig.shiftEntriesPath, params: {'month': month});
    return (resp.data as List).map((e) => ShiftEntry.fromJson(e as Map<String, dynamic>)).toList();
  }

  Future<ShiftEntry> createEntry({
    required String date,
    required int shiftTypeId,
    String? notes,
  }) async {
    final data = <String, dynamic>{
      'date': date,
      'shift_type_id': shiftTypeId,
    };
    if (notes != null) data['notes'] = notes;
    final resp = await _api.post(ApiConfig.shiftEntriesPath, data: data);
    return ShiftEntry.fromJson(resp.data as Map<String, dynamic>);
  }

  Future<void> deleteEntry(int id) async {
    await _api.delete('${ApiConfig.shiftEntriesPath}/$id');
  }
}
