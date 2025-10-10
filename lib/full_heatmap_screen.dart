import 'package:flutter/material.dart';

class FullHeatmapScreen extends StatelessWidget {
  final String imageUrl;
  const FullHeatmapScreen({super.key, required this.imageUrl});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text("Full Heatmap")),
      body: Center(
        child: InteractiveViewer(
          minScale: 0.5,
          maxScale: 4,
          child: Image.network(imageUrl, fit: BoxFit.contain),
        ),
      ),
    );
  }
}
