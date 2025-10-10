import 'dart:io' show File;
import 'package:flutter/foundation.dart' show kIsWeb;
import 'package:flutter/material.dart';
import 'package:share_plus/share_plus.dart';
import 'package:cross_file/cross_file.dart';
import 'package:pdf/widgets.dart' as pw;
import 'package:pdf/pdf.dart';
import 'package:path_provider/path_provider.dart';
import 'package:printing/printing.dart';
import 'dart:typed_data';

import 'report_model.dart';
import 'reports_screen.dart';

class FullReportScreen extends StatelessWidget {
  final ReportModel report;
  final int index;

  const FullReportScreen({
    super.key,
    required this.report,
    required this.index,
  });

  /// 🎨 Confidence color
  Color _getConfidenceColor(double conf) {
    if (conf >= 80) return Colors.green;
    if (conf >= 50) return Colors.orange;
    return Colors.redAccent;
  }

  /// 🧾 Build the PDF document
  Future<Uint8List> _buildPdf() async {
    final pdf = pw.Document();
    final confValue = double.tryParse(report.confidence) ?? 0.0;

    Uint8List? imageBytes;
    Uint8List? vizBytes;

    // ✅ Load local image bytes
    if (!kIsWeb) {
      if (report.imagePath.isNotEmpty &&
          !report.imagePath.startsWith("http") &&
          !report.imagePath.startsWith("data:")) {
        imageBytes = await File(report.imagePath).readAsBytes();
      }
      if (report.vizUrl.isNotEmpty &&
          !report.vizUrl.startsWith("http") &&
          !report.vizUrl.startsWith("data:")) {
        vizBytes = await File(report.vizUrl).readAsBytes();
      }
    }

    pdf.addPage(
      pw.MultiPage(
        build: (pw.Context ctx) => [
          pw.Center(
            child: pw.Text(
              "🩺 AI Diagnosis Report",
              style: pw.TextStyle(fontSize: 22, fontWeight: pw.FontWeight.bold),
            ),
          ),
          pw.SizedBox(height: 20),
          pw.Text(
            "🧾 Title: ${report.title}",
            style: pw.TextStyle(fontSize: 16),
          ),
          pw.Text(
            "📅 Date: ${report.date}",
            style: pw.TextStyle(color: PdfColors.grey),
          ),
          pw.SizedBox(height: 10),
          pw.Text(
            "🎯 Confidence: ${report.confidence}%",
            style: pw.TextStyle(
              fontSize: 14,
              color: PdfColor.fromInt(_getConfidenceColor(confValue).value),
            ),
          ),
          pw.SizedBox(height: 20),

          if (imageBytes != null) ...[
            pw.Text(
              "🩺 Original Image:",
              style: pw.TextStyle(fontWeight: pw.FontWeight.bold),
            ),
            pw.SizedBox(height: 8),
            pw.Center(child: pw.Image(pw.MemoryImage(imageBytes), width: 300)),
            pw.SizedBox(height: 20),
          ],

          if (vizBytes != null) ...[
            pw.Text(
              "🔥 AI Heatmap:",
              style: pw.TextStyle(fontWeight: pw.FontWeight.bold),
            ),
            pw.SizedBox(height: 8),
            pw.Center(child: pw.Image(pw.MemoryImage(vizBytes), width: 300)),
            pw.SizedBox(height: 20),
          ],

          pw.Text(
            "🧠 Explanation:",
            style: pw.TextStyle(fontSize: 16, fontWeight: pw.FontWeight.bold),
          ),
          pw.SizedBox(height: 8),
          pw.Text(
            report.explanation.isNotEmpty
                ? report.explanation
                : "No explanation provided.",
            style: const pw.TextStyle(fontSize: 14, height: 1.4),
          ),
        ],
      ),
    );

    return pdf.save();
  }

  /// 📄 Export report as PDF (Web + Mobile)
  Future<void> _exportToPDF(BuildContext context) async {
    try {
      final pdfBytes = await _buildPdf();

      if (kIsWeb) {
        // 🌐 Web: share directly
        await Printing.sharePdf(
          bytes: pdfBytes,
          filename: "AI_Report_${report.date}.pdf",
        );
      } else {
        // 📱 Mobile/Desktop: save and share
        final dir = await getTemporaryDirectory();
        final file = File("${dir.path}/AI_Report_${report.date}.pdf");
        await file.writeAsBytes(pdfBytes);
        await Share.shareXFiles([XFile(file.path)], text: "📄 AI Report PDF");
      }

      if (context.mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(
            content: Text("✅ Report exported as PDF successfully"),
          ),
        );
      }
    } catch (e) {
      if (context.mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text("❌ Failed to export PDF: $e"),
            backgroundColor: Colors.redAccent,
          ),
        );
      }
    }
  }

  /// 👁️ Preview PDF before saving
  void _previewPDF(BuildContext context) async {
    final pdfBytes = await _buildPdf();
    Navigator.push(
      context,
      MaterialPageRoute(
        builder: (_) => Scaffold(
          appBar: AppBar(title: const Text("📄 PDF Preview")),
          body: PdfPreview(
            build: (format) async => pdfBytes,
            allowPrinting: true,
            allowSharing: true,
            canChangePageFormat: false,
            canChangeOrientation: false,
          ),
        ),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final isNet =
        report.imagePath.startsWith("http") ||
        report.imagePath.startsWith("data:");
    final confValue = double.tryParse(report.confidence) ?? 0.0;

    return Scaffold(
      appBar: AppBar(
        title: const Text("Full Report"),
        actions: [
          IconButton(
            icon: const Icon(Icons.picture_as_pdf, color: Colors.orange),
            tooltip: "Export as PDF",
            onPressed: () => _exportToPDF(context),
          ),
          IconButton(
            icon: const Icon(Icons.preview, color: Colors.teal),
            tooltip: "Preview PDF",
            onPressed: () => _previewPDF(context),
          ),
          IconButton(
            icon: const Icon(Icons.share),
            tooltip: "Share Report",
            onPressed: () async {
              if (kIsWeb) {
                await Share.share(report.imagePath);
              } else {
                await Share.shareXFiles([XFile(report.imagePath)]);
              }
            },
          ),
          IconButton(
            icon: const Icon(Icons.delete, color: Colors.redAccent),
            tooltip: "Delete Report",
            onPressed: () async {
              final confirm = await showDialog<bool>(
                context: context,
                builder: (ctx) => AlertDialog(
                  title: const Text("Delete Report"),
                  content: const Text(
                    "Are you sure you want to delete this report?",
                  ),
                  actions: [
                    TextButton(
                      onPressed: () => Navigator.pop(ctx, false),
                      child: const Text("Cancel"),
                    ),
                    TextButton(
                      onPressed: () => Navigator.pop(ctx, true),
                      child: const Text(
                        "Delete",
                        style: TextStyle(color: Colors.redAccent),
                      ),
                    ),
                  ],
                ),
              );

              if (confirm == true) {
                await ReportStorage.deleteReport(index);
                if (context.mounted) {
                  Navigator.pushAndRemoveUntil(
                    context,
                    MaterialPageRoute(builder: (_) => const ReportsScreen()),
                    (route) => false,
                  );
                }
              }
            },
          ),
        ],
      ),
      body: ListView(
        padding: const EdgeInsets.all(16),
        children: [
          Text(
            report.title,
            style: const TextStyle(fontSize: 20, fontWeight: FontWeight.bold),
          ),
          const SizedBox(height: 6),
          Text("📅 ${report.date}", style: const TextStyle(color: Colors.grey)),
          const SizedBox(height: 16),

          ClipRRect(
            borderRadius: BorderRadius.circular(16),
            child: isNet
                ? Image.network(
                    report.imagePath,
                    width: double.infinity,
                    height: 250,
                    fit: BoxFit.cover,
                  )
                : Image.file(
                    File(report.imagePath),
                    width: double.infinity,
                    height: 250,
                    fit: BoxFit.cover,
                  ),
          ),

          const SizedBox(height: 16),

          if (report.vizUrl.isNotEmpty)
            Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                const Text(
                  "🔥 AI Heatmap (Focus Areas)",
                  style: TextStyle(fontWeight: FontWeight.w600, fontSize: 16),
                ),
                const SizedBox(height: 8),
                ClipRRect(
                  borderRadius: BorderRadius.circular(16),
                  child: Image.network(
                    report.vizUrl,
                    width: double.infinity,
                    height: 250,
                    fit: BoxFit.cover,
                    errorBuilder: (_, __, ___) => const Center(
                      child: Text(
                        "⚠️ Failed to load heatmap",
                        style: TextStyle(color: Colors.redAccent),
                      ),
                    ),
                  ),
                ),
              ],
            ),

          const SizedBox(height: 20),

          const Text(
            "🎯 Confidence",
            style: TextStyle(fontWeight: FontWeight.w600, fontSize: 16),
          ),
          const SizedBox(height: 8),
          ClipRRect(
            borderRadius: BorderRadius.circular(8),
            child: LinearProgressIndicator(
              value: confValue / 100,
              backgroundColor: Colors.grey.shade300,
              valueColor: AlwaysStoppedAnimation<Color>(
                _getConfidenceColor(confValue),
              ),
              minHeight: 10,
            ),
          ),
          const SizedBox(height: 8),
          Text(
            "${report.confidence}%",
            style: TextStyle(
              fontWeight: FontWeight.bold,
              color: _getConfidenceColor(confValue),
            ),
          ),

          const SizedBox(height: 20),

          if (report.explanation.isNotEmpty)
            Container(
              width: double.infinity,
              padding: const EdgeInsets.all(14),
              decoration: BoxDecoration(
                color: Colors.blueGrey.withOpacity(0.1),
                borderRadius: BorderRadius.circular(12),
              ),
              child: Text(
                "🧠 ${report.explanation}",
                style: const TextStyle(fontSize: 15, height: 1.5),
              ),
            ),
        ],
      ),
    );
  }
}
