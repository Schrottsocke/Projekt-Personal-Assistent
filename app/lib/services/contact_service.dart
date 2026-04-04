import '../config/api_config.dart';
import '../models/contact.dart';
import 'api_service.dart';

class ContactService {
  final ApiService _api;
  ContactService(this._api);

  Future<List<Contact>> getAll({String? search}) async {
    final params = <String, dynamic>{};
    if (search != null && search.isNotEmpty) params['search'] = search;
    final resp = await _api.get(ApiConfig.contactsPath, params: params);
    return (resp.data as List).map((e) => Contact.fromJson(e as Map<String, dynamic>)).toList();
  }

  Future<Contact> get(int id) async {
    final resp = await _api.get('${ApiConfig.contactsPath}/$id');
    return Contact.fromJson(resp.data as Map<String, dynamic>);
  }

  Future<Contact> create({
    required String name,
    String? email,
    String? phone,
    String? notes,
    List<String>? tags,
  }) async {
    final data = <String, dynamic>{'name': name};
    if (email != null) data['email'] = email;
    if (phone != null) data['phone'] = phone;
    if (notes != null) data['notes'] = notes;
    if (tags != null) data['tags'] = tags;
    final resp = await _api.post(ApiConfig.contactsPath, data: data);
    return Contact.fromJson(resp.data as Map<String, dynamic>);
  }

  Future<Contact> update(int id, {
    String? name,
    String? email,
    String? phone,
    String? notes,
    List<String>? tags,
  }) async {
    final data = <String, dynamic>{};
    if (name != null) data['name'] = name;
    if (email != null) data['email'] = email;
    if (phone != null) data['phone'] = phone;
    if (notes != null) data['notes'] = notes;
    if (tags != null) data['tags'] = tags;
    final resp = await _api.patch('${ApiConfig.contactsPath}/$id', data: data);
    return Contact.fromJson(resp.data as Map<String, dynamic>);
  }

  Future<void> delete(int id) async {
    await _api.delete('${ApiConfig.contactsPath}/$id');
  }
}
