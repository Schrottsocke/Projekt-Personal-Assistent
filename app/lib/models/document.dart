class ScannedDocument {
  final int id;
  final String docType; // invoice, letter, contract, medical, other
  final String? sender;
  final double? amount;
  final String? ocrText;
  final String? driveFileId;
  final String? fileName;
  final DateTime createdAt;

  const ScannedDocument({
    required this.id,
    required this.docType,
    this.sender,
    this.amount,
    this.ocrText,
    this.driveFileId,
    this.fileName,
    required this.createdAt,
  });

  factory ScannedDocument.fromJson(Map<String, dynamic> j) => ScannedDocument(
        id: j['id'] as int,
        docType: j['doc_type'] as String? ?? 'other',
        sender: j['sender'] as String?,
        amount: j['amount'] != null ? (j['amount'] as num).toDouble() : null,
        ocrText: j['ocr_text'] as String?,
        driveFileId: j['drive_file_id'] as String?,
        fileName: j['file_name'] as String?,
        createdAt: DateTime.parse(j['created_at'] as String),
      );

  String get docTypeLabel => switch (docType) {
        'invoice' => 'Rechnung',
        'letter' => 'Brief',
        'contract' => 'Vertrag',
        'medical' => 'Arztbrief',
        _ => 'Sonstiges',
      };
}
