import '../config/api_config.dart';
import '../models/document.dart';
import 'api_service.dart';

class DocumentService {
  final ApiService _api;
  DocumentService(this._api);

  Future<List<ScannedDocument>> getAll({String? docType}) async {
    final params = <String, dynamic>{};
    if (docType != null) params['doc_type'] = docType;
    final resp = await _api.get(ApiConfig.documentsPath, params: params);
    return (resp.data as List)
        .map((e) => ScannedDocument.fromJson(e as Map<String, dynamic>))
        .toList();
  }

  Future<ScannedDocument> get(int id) async {
    final resp = await _api.get('${ApiConfig.documentsPath}/$id');
    return ScannedDocument.fromJson(resp.data as Map<String, dynamic>);
  }

  /// Upload is a placeholder -- actual camera/file upload will be added
  /// once the image_picker dependency is integrated.
  Future<ScannedDocument> upload(String filePath, String fileName) async {
    final resp = await _api.post(
      ApiConfig.documentsUploadPath,
      data: {'file_path': filePath, 'file_name': fileName},
    );
    return ScannedDocument.fromJson(resp.data as Map<String, dynamic>);
  }

  Future<Map<String, dynamic>> triggerAction(int id, String action) async {
    final resp = await _api.post(
      '${ApiConfig.documentsPath}/$id/action',
      data: {'action': action},
    );
    return resp.data as Map<String, dynamic>;
  }
}
