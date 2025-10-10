import 'dart:convert';
import 'package:flutter/material.dart';
import 'package:http/http.dart' as http;

class AiChatScreen extends StatefulWidget {
  const AiChatScreen({super.key});

  @override
  State<AiChatScreen> createState() => _AiChatScreenState();
}

class _AiChatScreenState extends State<AiChatScreen> {
  final List<Map<String, dynamic>> _messages = [
    {
      "text":
          "👋 Hello! I’m your AI Health Assistant.\nDescribe your symptoms or ask health questions. I’ll give you safe, helpful info — but remember, I’m not a doctor.",
      "isUser": false
    },
  ];
  final TextEditingController _controller = TextEditingController();
  bool _isLoading = false;

  // 🧠 Your API key here (Gemini or OpenAI)
  static const String _apiKey = "YOUR_API_KEY";

  // ⚙️ Use OpenAI (you can switch to Gemini below)
  Future<String> _getAiResponse(String prompt) async {
    try {
      final url = Uri.parse("https://api.openai.com/v1/chat/completions");
      final response = await http.post(
        url,
        headers: {
          "Content-Type": "application/json",
          "Authorization": "Bearer $_apiKey",
        },
        body: jsonEncode({
          "model": "gpt-3.5-turbo",
          "messages": [
            {
              "role": "system",
              "content":
                  "You are an AI Health Assistant. Be kind, clear, and safe. Always suggest consulting a doctor for serious symptoms."
            },
            {"role": "user", "content": prompt}
          ],
          "max_tokens": 200,
        }),
      );

      if (response.statusCode == 200) {
        final data = jsonDecode(response.body);
        final msg = data["choices"][0]["message"]["content"];
        return msg.toString().trim();
      } else {
        return "⚠️ Unable to connect to AI. Try again later.";
      }
    } catch (e) {
      return "⚠️ Error: $e";
    }
  }

  void _sendMessage() async {
    if (_controller.text.trim().isEmpty) return;
    final text = _controller.text.trim();
    setState(() {
      _messages.add({"text": text, "isUser": true});
      _controller.clear();
      _isLoading = true;
    });

    final reply = await _getAiResponse(text);
    setState(() {
      _messages.add({"text": reply, "isUser": false});
      _isLoading = false;
    });
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text("AI Health Assistant 🤖"),
        backgroundColor: Colors.blueAccent,
      ),
      body: Column(
        children: [
          Expanded(
            child: ListView.builder(
              padding: const EdgeInsets.all(16),
              itemCount: _messages.length,
              itemBuilder: (context, index) {
                final msg = _messages[index];
                return Align(
                  alignment: msg["isUser"]
                      ? Alignment.centerRight
                      : Alignment.centerLeft,
                  child: Container(
                    margin: const EdgeInsets.symmetric(vertical: 6),
                    padding: const EdgeInsets.all(12),
                    constraints:
                        const BoxConstraints(maxWidth: 300, minWidth: 60),
                    decoration: BoxDecoration(
                      color: msg["isUser"]
                          ? Colors.blueAccent
                          : Colors.grey.shade200,
                      borderRadius: BorderRadius.circular(16),
                    ),
                    child: Text(
                      msg["text"],
                      style: TextStyle(
                        color: msg["isUser"] ? Colors.white : Colors.black87,
                        fontSize: 15,
                        height: 1.4,
                      ),
                    ),
                  ),
                );
              },
            ),
          ),
          if (_isLoading)
            const Padding(
              padding: EdgeInsets.all(8),
              child: CircularProgressIndicator(),
            ),
          _buildInputBar(),
        ],
      ),
    );
  }

  Widget _buildInputBar() {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
      decoration: BoxDecoration(
        color: Colors.grey.shade100,
        border: const Border(top: BorderSide(color: Colors.grey, width: 0.2)),
      ),
      child: Row(
        children: [
          Expanded(
            child: TextField(
              controller: _controller,
              decoration: const InputDecoration(
                hintText: "Type your symptoms or question...",
                border: InputBorder.none,
              ),
              onSubmitted: (_) => _sendMessage(),
            ),
          ),
          IconButton(
            icon: const Icon(Icons.send, color: Colors.blueAccent),
            onPressed: _sendMessage,
          ),
        ],
      ),
    );
  }
}
