import 'dart:async';
import 'package:flutter/material.dart';

import 'ai_scan_screen.dart';
import 'reports_screen.dart';

/// =====================================================================
/// 🔹 Simple in-memory profile store (user) – used by Profile pages
/// =====================================================================
class UserProfileStore extends ChangeNotifier {
  String name = "Aman Singh";
  String email = "aman@example.com";
  String phone = "+91 9876543210";
  String avatarUrl = 'https://i.pravatar.cc/150?img=5';

  void update({String? name, String? email, String? phone, String? avatarUrl}) {
    if (name != null) this.name = name;
    if (email != null) this.email = email;
    if (phone != null) this.phone = phone;
    if (avatarUrl != null) this.avatarUrl = avatarUrl;
    notifyListeners();
  }
}

final UserProfileStore userProfileStore = UserProfileStore();

/// =====================================================================
/// 💎 Plan store – single source of truth for subscription plan
/// =====================================================================
class PlanStore extends ChangeNotifier {
  String currentPlan = "Free"; // Free | Pro | Premium

  void updatePlan(String newPlan) {
    if (newPlan.isEmpty) return;
    currentPlan = newPlan;
    notifyListeners();
  }
}

final PlanStore planStore = PlanStore();

/// =====================================================================
/// 🩺 Demo doctor database (unchanged)
/// =====================================================================
final List<Map<String, dynamic>> doctorDatabase = <Map<String, dynamic>>[
  {
    "name": "Dr. Arjun Singh",
    "speciality": "General Physician",
    "qualification": "MBBS, MD (Medicine)",
    "rating": 4.8,
    "experience": "10+ Years",
    "country": "🇮🇳 India",
    "city": "New Delhi",
    "languages": ["English", "Hindi"],
    "verified": true,
    "available": "Mon–Fri, 10:00–17:00",
    "slots": ["10:00 AM", "11:30 AM", "2:00 PM", "4:00 PM"],
    "clinic": "HealthyLife Clinic, Connaught Place, New Delhi",
    "reviews": [
      {
        "name": "Rajesh",
        "comment": "Very professional and polite!",
        "stars": 5,
      },
      {"name": "Sneha", "comment": "Explains everything clearly.", "stars": 4},
    ],
    "mode": ["In-Person", "Online"],
    "image": "https://i.pravatar.cc/150?img=12",
    "fee": 500,
    "bio":
        "Renowned general physician with 10+ years experience in lifestyle and chronic disease management. Special interest in diabetes, hypertension and preventive care.",
  },
  {
    "name": "Anjali Sharma",
    "speciality": "Therapist",
    "qualification": "M.Phil (Clinical Psychology)",
    "rating": 4.7,
    "experience": "7+ Years",
    "country": "🇮🇳 India",
    "city": "Mumbai",
    "languages": ["English", "Hindi"],
    "verified": true,
    "available": "Tue–Sat, 09:00–16:00",
    "slots": ["9:30 AM", "11:00 AM", "1:00 PM", "3:30 PM"],
    "clinic": "MindCare Centre, Andheri West, Mumbai",
    "reviews": [
      {
        "name": "Priya",
        "comment": "Helped me overcome my anxiety!",
        "stars": 5,
      },
      {"name": "Amit", "comment": "Kind and understanding.", "stars": 4},
    ],
    "mode": ["Online"],
    "image": "https://i.pravatar.cc/150?img=47",
    "fee": 700,
    "bio":
        "Certified clinical psychologist focusing on anxiety, depression and CBT. Known for empathetic, evidence-based care tailored to individual needs.",
  },
  {
    "name": "Dr. Emily Carter",
    "speciality": "Cardiologist",
    "qualification": "MBBS, DM (Cardiology)",
    "rating": 4.9,
    "experience": "12+ Years",
    "country": "🇺🇸 USA",
    "city": "Austin",
    "languages": ["English", "Spanish"],
    "verified": true,
    "available": "Mon–Sat, 08:00–16:00",
    "slots": ["8:30 AM", "10:00 AM", "1:30 PM", "3:00 PM"],
    "clinic": "HeartWell Institute, Downtown Austin",
    "reviews": [
      {
        "name": "Chris",
        "comment": "Clear plan and great bedside manner.",
        "stars": 5,
      },
    ],
    "mode": ["In-Person"],
    "image": "https://i.pravatar.cc/150?img=36",
    "fee": 800,
    "bio":
        "Interventional cardiologist with expertise in cardiac imaging, heart failure and preventive cardiology.",
  },
  {
    "name": "Dr. Luca Rossi",
    "speciality": "Dermatologist",
    "qualification": "MD (Dermatology)",
    "rating": 4.6,
    "experience": "9+ Years",
    "country": "🇮🇹 Italy",
    "city": "Milan",
    "languages": ["Italian", "English"],
    "verified": false,
    "available": "Wed–Sun, 11:00–18:00",
    "slots": ["11:00 AM", "12:30 PM", "4:30 PM"],
    "clinic": "DermaGlow Clinic, Porta Nuova, Milan",
    "reviews": [],
    "mode": ["In-Person", "Online"],
    "image": "https://i.pravatar.cc/150?img=22",
    "fee": 650,
    "bio":
        "General and cosmetic dermatology. Special focus on acne, hair loss and minimally invasive procedures.",
  },
];

List<Map<String, dynamic>> demoDoctors() => doctorDatabase;

/// =====================================================================
/// 🏠 Main Home container with bottom nav
/// =====================================================================
class HomePage extends StatefulWidget {
  const HomePage({super.key});
  @override
  State<HomePage> createState() => _HomePageState();
}

class _HomePageState extends State<HomePage> {
  int _selectedIndex = 0;

  final List<Widget> _pages = const [
    HomeScreen(),
    ChatScreen(),
    AppointmentScreen(),
    ProfileScreen(),
  ];

  void _onItemTapped(int index) => setState(() => _selectedIndex = index);

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: _pages[_selectedIndex],
      bottomNavigationBar: BottomNavigationBar(
        currentIndex: _selectedIndex,
        onTap: _onItemTapped,
        type: BottomNavigationBarType.fixed,
        selectedItemColor: Colors.blueAccent,
        unselectedItemColor: Colors.grey,
        items: const [
          BottomNavigationBarItem(icon: Icon(Icons.home), label: "Home"),
          BottomNavigationBarItem(icon: Icon(Icons.chat_bubble), label: "Chat"),
          BottomNavigationBarItem(
            icon: Icon(Icons.calendar_today),
            label: "Appointments",
          ),
          BottomNavigationBarItem(icon: Icon(Icons.person), label: "Profile"),
        ],
      ),
    );
  }
}

/// =====================================================================
/// 🏠 Home screen
/// =====================================================================
class HomeScreen extends StatelessWidget {
  const HomeScreen({super.key});

  @override
  Widget build(BuildContext context) {
    final doctors = demoDoctors();

    return SafeArea(
      child: SingleChildScrollView(
        padding: const EdgeInsets.all(20.0),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Text(
              "Health Dashboard",
              style: TextStyle(fontSize: 28, fontWeight: FontWeight.bold),
            ),
            const SizedBox(height: 8),
            const Text(
              "Your daily health assistant 👇",
              style: TextStyle(fontSize: 16, color: Colors.grey),
            ),
            const SizedBox(height: 20),

            // 💎 Plan banner (reactive)
            const PlanBanner(),
            const SizedBox(height: 20),

            Container(
              padding: const EdgeInsets.all(16),
              decoration: BoxDecoration(
                color: Colors.blue[50],
                borderRadius: BorderRadius.circular(12),
              ),
              child: Row(
                children: [
                  Icon(Icons.health_and_safety, color: Colors.blue[700]),
                  const SizedBox(width: 12),
                  const Expanded(
                    child: Text(
                      "Last AI Scan: Normal 🟢\nBP: 118/76 | Sugar: Normal | HR: 78 bpm",
                      style: TextStyle(fontSize: 14, height: 1.4),
                    ),
                  ),
                ],
              ),
            ),
            const SizedBox(height: 20),

            if (doctors.isNotEmpty)
              Container(
                padding: const EdgeInsets.all(16),
                decoration: BoxDecoration(
                  color: Colors.orange[50],
                  borderRadius: BorderRadius.circular(12),
                ),
                child: Row(
                  children: [
                    const Icon(Icons.calendar_month, color: Colors.orange),
                    const SizedBox(width: 12),
                    Expanded(
                      child: Text(
                        "Next Appointment: Tomorrow, 3PM\n${doctors.first["name"]} (${doctors.first["speciality"]})",
                        style: const TextStyle(fontSize: 14, height: 1.4),
                      ),
                    ),
                    const Icon(
                      Icons.arrow_forward_ios,
                      size: 16,
                      color: Colors.orange,
                    ),
                  ],
                ),
              ),
            const SizedBox(height: 24),

            TextField(
              decoration: InputDecoration(
                hintText: "Search services, doctors, reports...",
                prefixIcon: const Icon(Icons.search),
                suffixIcon: const Icon(Icons.qr_code_scanner),
                border: OutlineInputBorder(
                  borderRadius: BorderRadius.circular(12),
                ),
                filled: true,
                fillColor: Colors.grey[100],
              ),
            ),
            const SizedBox(height: 24),

            const Text(
              "Suggestions",
              style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold),
            ),
            const SizedBox(height: 12),

            GridView(
              shrinkWrap: true,
              physics: const NeverScrollableScrollPhysics(),
              gridDelegate: const SliverGridDelegateWithFixedCrossAxisCount(
                crossAxisCount: 2,
                mainAxisSpacing: 16,
                crossAxisSpacing: 16,
                childAspectRatio: 1.15,
              ),
              children: [
                _SuggestionCard(
                  icon: Icons.document_scanner,
                  title: "AI Scan",
                  onTap: () {
                    // 🔗 Pass live plan into AI Scan
                    Navigator.push(
                      context,
                      MaterialPageRoute(
                        builder: (_) =>
                            AiScanScreen(plan: planStore.currentPlan),
                      ),
                    );
                  },
                ),
                _SuggestionCard(
                  icon: Icons.bar_chart,
                  title: "Reports",
                  onTap: () => Navigator.push(
                    context,
                    MaterialPageRoute(builder: (_) => const ReportsScreen()),
                  ),
                ),
                _SuggestionCard(
                  icon: Icons.local_hospital,
                  title: "Book Doctor",
                  onTap: () => Navigator.push(
                    context,
                    MaterialPageRoute(
                      builder: (_) => const AppointmentScreen(),
                    ),
                  ),
                ),
                _SuggestionCard(
                  icon: Icons.psychology,
                  title: "Find Therapist",
                  onTap: () => Navigator.push(
                    context,
                    MaterialPageRoute(
                      builder: (_) =>
                          const AppointmentScreen(filter: "Therapist"),
                    ),
                  ),
                ),
              ],
            ),

            const SizedBox(height: 24),

            const Text(
              "Appointments",
              style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold),
            ),
            const SizedBox(height: 12),
            if (doctors.isNotEmpty)
              ...doctors
                  .take(2)
                  .map(
                    (d) => _HomeAppointmentTile(
                      doctor: d,
                      onTap: () => Navigator.push(
                        context,
                        MaterialPageRoute(
                          builder: (_) => DoctorDetailPage(doctor: d),
                        ),
                      ),
                    ),
                  ),
          ],
        ),
      ),
    );
  }
}

/// =====================================================================
/// 💬 Chat Screen
/// =====================================================================
class ChatScreen extends StatefulWidget {
  const ChatScreen({super.key});
  @override
  State<ChatScreen> createState() => _ChatScreenState();
}

class _ChatScreenState extends State<ChatScreen> {
  final List<Map<String, dynamic>> _messages = [
    {"text": "Hello 👋, how are you feeling today?", "isUser": false},
  ];
  final TextEditingController _controller = TextEditingController();

  void _sendMessage() {
    final txt = _controller.text.trim();
    if (txt.isEmpty) return;
    setState(() {
      _messages.add({"text": txt, "isUser": true});
      _controller.clear();
    });
    Future.delayed(const Duration(milliseconds: 400), () {
      final reply = _getReply(txt);
      setState(() => _messages.add({"text": reply, "isUser": false}));
    });
  }

  String _getReply(String text) {
    final msg = text.toLowerCase();
    if (msg.contains("doctor"))
      return "You can book a doctor from Appointments 📅.";
    if (msg.contains("scan")) return "Tap 'AI Scan' on Home to start 🩺.";
    if (msg.contains("report")) return "Check 'Reports' section 📊.";
    return "Got it ✅. Need anything else?";
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text("Chat Assistant")),
      body: Column(
        children: [
          Expanded(
            child: ListView.builder(
              padding: const EdgeInsets.all(12),
              itemCount: _messages.length,
              itemBuilder: (context, i) {
                final msg = _messages[i];
                final bool isUser = msg["isUser"] == true;
                return Align(
                  alignment: isUser
                      ? Alignment.centerRight
                      : Alignment.centerLeft,
                  child: Container(
                    margin: const EdgeInsets.symmetric(vertical: 4),
                    padding: const EdgeInsets.all(12),
                    decoration: BoxDecoration(
                      color: isUser ? Colors.blue[200] : Colors.grey[300],
                      borderRadius: BorderRadius.circular(16),
                    ),
                    child: Text(
                      msg["text"] as String,
                      style: const TextStyle(fontSize: 16),
                    ),
                  ),
                );
              },
            ),
          ),
          Padding(
            padding: const EdgeInsets.symmetric(horizontal: 12.0, vertical: 4),
            child: Wrap(
              spacing: 8,
              children: [
                ActionChip(
                  label: const Text("AI Scan"),
                  onPressed: () => _controller.text = "AI Scan",
                ),
                ActionChip(
                  label: const Text("Reports"),
                  onPressed: () => _controller.text = "Open Reports",
                ),
                ActionChip(
                  label: const Text("Book Doctor"),
                  onPressed: () => _controller.text = "Book Doctor",
                ),
              ],
            ),
          ),
          Container(
            color: Colors.grey[100],
            padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 6),
            child: Row(
              children: [
                Expanded(
                  child: TextField(
                    controller: _controller,
                    decoration: const InputDecoration(
                      hintText: "Type your message...",
                      border: InputBorder.none,
                    ),
                  ),
                ),
                IconButton(
                  icon: const Icon(Icons.send, color: Colors.blue),
                  onPressed: _sendMessage,
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}

/// =====================================================================
/// 📅 Appointments
/// =====================================================================
class AppointmentScreen extends StatefulWidget {
  final String? filter;
  const AppointmentScreen({super.key, this.filter});

  @override
  State<AppointmentScreen> createState() => _AppointmentScreenState();
}

class _AppointmentScreenState extends State<AppointmentScreen> {
  final TextEditingController _searchController = TextEditingController();
  List<Map<String, dynamic>> _filteredDoctors = <Map<String, dynamic>>[];

  @override
  void initState() {
    super.initState();
    _filteredDoctors = widget.filter == null
        ? demoDoctors()
        : demoDoctors()
              .where(
                (d) => (d["speciality"]?.toString().toLowerCase() ?? "")
                    .contains(widget.filter!.toLowerCase()),
              )
              .toList();
    _searchController.addListener(_onSearchChanged);
  }

  void _onSearchChanged() {
    final query = _searchController.text.toLowerCase();
    setState(() {
      _filteredDoctors = widget.filter == null
          ? demoDoctors()
                .where(
                  (d) =>
                      (d["name"]?.toString().toLowerCase() ?? "").contains(
                        query,
                      ) ||
                      (d["speciality"]?.toString().toLowerCase() ?? "")
                          .contains(query),
                )
                .toList()
          : demoDoctors()
                .where(
                  (d) =>
                      (d["speciality"]?.toString().toLowerCase() ?? "")
                          .contains(widget.filter!.toLowerCase()) &&
                      ((d["name"]?.toString().toLowerCase() ?? "").contains(
                            query,
                          ) ||
                          (d["speciality"]?.toString().toLowerCase() ?? "")
                              .contains(query)),
                )
                .toList();
    });
  }

  @override
  void dispose() {
    _searchController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: Text(
          widget.filter == null ? "Book Appointments" : "Find ${widget.filter}",
        ),
        centerTitle: true,
        backgroundColor: Colors.blueAccent,
      ),
      body: Column(
        children: [
          Padding(
            padding: const EdgeInsets.all(16.0),
            child: TextField(
              controller: _searchController,
              decoration: InputDecoration(
                hintText: "Search doctors by name or speciality...",
                prefixIcon: const Icon(Icons.search),
                border: OutlineInputBorder(
                  borderRadius: BorderRadius.circular(12),
                ),
                filled: true,
                fillColor: Colors.grey[100],
              ),
            ),
          ),
          Expanded(
            child: ListView.builder(
              padding: const EdgeInsets.all(16),
              itemCount: _filteredDoctors.length,
              itemBuilder: (context, index) {
                final Map<String, dynamic> doc = _filteredDoctors[index];
                return _DoctorCard(doctor: doc);
              },
            ),
          ),
        ],
      ),
    );
  }
}

class _DoctorCard extends StatelessWidget {
  final Map<String, dynamic> doctor;
  const _DoctorCard({required this.doctor});

  @override
  Widget build(BuildContext context) {
    return Card(
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
      margin: const EdgeInsets.only(bottom: 16),
      elevation: 2,
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                CircleAvatar(
                  radius: 35,
                  backgroundImage: NetworkImage(doctor["image"] as String),
                ),
                const SizedBox(width: 16),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Row(
                        children: [
                          Expanded(
                            child: Text(
                              doctor["name"] as String,
                              style: const TextStyle(
                                fontSize: 18,
                                fontWeight: FontWeight.bold,
                              ),
                            ),
                          ),
                          if (doctor["verified"] == true)
                            const Icon(
                              Icons.verified,
                              size: 18,
                              color: Colors.blueAccent,
                            ),
                        ],
                      ),
                      Text(
                        doctor["speciality"] as String,
                        style: const TextStyle(color: Colors.grey),
                      ),
                      Text(
                        doctor["qualification"] as String,
                        style: const TextStyle(
                          fontSize: 12,
                          color: Colors.grey,
                        ),
                      ),
                    ],
                  ),
                ),
              ],
            ),
            const SizedBox(height: 8),
            Text("${doctor["country"]} • ${doctor["city"]}"),
            const SizedBox(height: 8),
            Row(
              children: [
                const Icon(Icons.star, color: Colors.amber, size: 18),
                const SizedBox(width: 4),
                Text("${doctor["rating"]}"),
                const SizedBox(width: 12),
                const Icon(Icons.work_history, color: Colors.blue, size: 18),
                const SizedBox(width: 4),
                Text(doctor["experience"] as String),
              ],
            ),
            const SizedBox(height: 12),
            Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                Row(
                  children: [
                    const Icon(
                      Icons.access_time,
                      color: Colors.green,
                      size: 18,
                    ),
                    const SizedBox(width: 6),
                    Text(
                      doctor["available"] as String,
                      style: const TextStyle(fontSize: 12, color: Colors.grey),
                    ),
                  ],
                ),
                Text(
                  "₹${doctor["fee"]}/visit",
                  style: const TextStyle(
                    fontWeight: FontWeight.bold,
                    color: Colors.blueAccent,
                  ),
                ),
              ],
            ),
            const SizedBox(height: 12),
            SizedBox(
              width: double.infinity,
              child: ElevatedButton.icon(
                style: ElevatedButton.styleFrom(
                  backgroundColor: Colors.blueAccent,
                  shape: RoundedRectangleBorder(
                    borderRadius: BorderRadius.circular(12),
                  ),
                ),
                onPressed: () => Navigator.push(
                  context,
                  MaterialPageRoute(
                    builder: (_) => DoctorDetailPage(doctor: doctor),
                  ),
                ),
                icon: const Icon(Icons.calendar_month),
                label: const Text("Book Appointment"),
              ),
            ),
          ],
        ),
      ),
    );
  }
}

/// =====================================================================
/// 🧑‍⚕️ Doctor details
/// =====================================================================
class DoctorDetailPage extends StatefulWidget {
  final Map<String, dynamic> doctor;
  const DoctorDetailPage({super.key, required this.doctor});

  @override
  State<DoctorDetailPage> createState() => _DoctorDetailPageState();
}

class _DoctorDetailPageState extends State<DoctorDetailPage> {
  DateTime selectedDate = DateTime.now();
  String? selectedSlot;

  @override
  Widget build(BuildContext context) {
    final d = widget.doctor;
    final List<String> slotList = (d["slots"] as List<dynamic>)
        .map((e) => e.toString())
        .toList();

    return Scaffold(
      appBar: AppBar(title: Text(d["name"] as String)),
      body: SingleChildScrollView(
        padding: const EdgeInsets.all(20),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Center(
              child: Column(
                children: [
                  CircleAvatar(
                    radius: 60,
                    backgroundImage: NetworkImage(d["image"] as String),
                  ),
                  const SizedBox(height: 12),
                  Row(
                    mainAxisAlignment: MainAxisAlignment.center,
                    children: [
                      Text(
                        d["name"] as String,
                        style: const TextStyle(
                          fontSize: 22,
                          fontWeight: FontWeight.bold,
                        ),
                      ),
                      const SizedBox(width: 6),
                      if (d["verified"] == true)
                        const Icon(
                          Icons.verified,
                          color: Colors.blueAccent,
                          size: 18,
                        ),
                    ],
                  ),
                  Text(
                    d["speciality"] as String,
                    style: const TextStyle(color: Colors.grey),
                  ),
                  Text(
                    d["qualification"] as String,
                    style: const TextStyle(color: Colors.grey),
                  ),
                ],
              ),
            ),
            const SizedBox(height: 16),
            Text(d["bio"] as String, style: const TextStyle(height: 1.4)),
            const Divider(height: 32),

            ListTile(
              leading: const Icon(Icons.access_time, color: Colors.green),
              title: const Text("Available"),
              subtitle: Text(d["available"] as String),
            ),
            ListTile(
              leading: const Icon(Icons.currency_rupee, color: Colors.orange),
              title: const Text("Consultation Fee"),
              subtitle: Text("₹${d["fee"]} per session"),
            ),
            ListTile(
              leading: const Icon(Icons.location_on, color: Colors.red),
              title: const Text("Clinic"),
              subtitle: Text(d["clinic"] as String),
            ),
            ListTile(
              leading: const Icon(Icons.video_call, color: Colors.blue),
              title: const Text("Consultation Mode"),
              subtitle: Text(
                ((d["mode"] as List<dynamic>).map((e) => e.toString()).toList())
                    .join(", "),
              ),
            ),
            ListTile(
              leading: const Icon(Icons.language, color: Colors.purple),
              title: const Text("Languages"),
              subtitle: Text(
                ((d["languages"] as List<dynamic>)
                        .map((e) => e.toString())
                        .toList())
                    .join(", "),
              ),
            ),

            const Divider(height: 32),

            const Text(
              "Select Date",
              style: TextStyle(fontSize: 16, fontWeight: FontWeight.bold),
            ),
            const SizedBox(height: 8),
            OutlinedButton.icon(
              onPressed: () async {
                final picked = await showDatePicker(
                  context: context,
                  initialDate: selectedDate,
                  firstDate: DateTime.now(),
                  lastDate: DateTime.now().add(const Duration(days: 30)),
                );
                if (picked != null) setState(() => selectedDate = picked);
              },
              icon: const Icon(Icons.calendar_today),
              label: Text(
                "${selectedDate.day}/${selectedDate.month}/${selectedDate.year}",
              ),
            ),
            const SizedBox(height: 16),

            const Text(
              "Available Time Slots",
              style: TextStyle(fontSize: 16, fontWeight: FontWeight.bold),
            ),
            const SizedBox(height: 8),
            Wrap(
              spacing: 10,
              runSpacing: 8,
              children: slotList.map((slot) {
                final sel = selectedSlot == slot;
                return ChoiceChip(
                  label: Text(slot),
                  selected: sel,
                  selectedColor: Colors.blueAccent,
                  onSelected: (_) => setState(() => selectedSlot = slot),
                );
              }).toList(),
            ),
            const SizedBox(height: 24),

            SizedBox(
              width: double.infinity,
              child: ElevatedButton.icon(
                icon: const Icon(Icons.check_circle_outline),
                label: const Text("Confirm Booking"),
                style: ElevatedButton.styleFrom(
                  backgroundColor: Colors.blueAccent,
                  padding: const EdgeInsets.symmetric(vertical: 14),
                  shape: RoundedRectangleBorder(
                    borderRadius: BorderRadius.circular(12),
                  ),
                ),
                onPressed: selectedSlot == null
                    ? null
                    : () {
                        final date =
                            "${selectedDate.day}/${selectedDate.month}/${selectedDate.year}";
                        ScaffoldMessenger.of(context).showSnackBar(
                          SnackBar(
                            content: Text(
                              "✅ Appointment booked with ${d["name"]} on $date at $selectedSlot",
                            ),
                          ),
                        );
                      },
              ),
            ),

            const Divider(height: 32),

            const Text(
              "Patient Reviews",
              style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold),
            ),
            const SizedBox(height: 8),
            if ((d["reviews"] as List).isEmpty)
              const Text(
                "No reviews yet.",
                style: TextStyle(color: Colors.grey),
              ),
            Column(
              children: (d["reviews"] as List<dynamic>).map((raw) {
                final r = raw as Map<String, dynamic>;
                return ListTile(
                  leading: const Icon(Icons.person, color: Colors.blue),
                  title: Text(r["name"] as String),
                  subtitle: Text(r["comment"] as String),
                  trailing: Row(
                    mainAxisSize: MainAxisSize.min,
                    children: List.generate(
                      (r["stars"] as int),
                      (_) =>
                          const Icon(Icons.star, color: Colors.amber, size: 16),
                    ),
                  ),
                );
              }).toList(),
            ),
          ],
        ),
      ),
    );
  }
}

/// =====================================================================
/// 👤 Profile
/// =====================================================================
class ProfileScreen extends StatefulWidget {
  const ProfileScreen({super.key});
  @override
  State<ProfileScreen> createState() => _ProfileScreenState();
}

class _ProfileScreenState extends State<ProfileScreen> {
  bool _darkMode = false;

  void _logout(BuildContext context) {
    showDialog(
      context: context,
      builder: (_) => AlertDialog(
        title: const Text("Logout"),
        content: const Text("Are you sure you want to log out?"),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context),
            child: const Text("Cancel"),
          ),
          TextButton(
            onPressed: () {
              Navigator.pop(context);
              ScaffoldMessenger.of(context).showSnackBar(
                const SnackBar(content: Text("✅ Logged out successfully")),
              );
            },
            child: const Text("Logout", style: TextStyle(color: Colors.red)),
          ),
        ],
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    return AnimatedBuilder(
      animation: userProfileStore,
      builder: (context, _) {
        return Scaffold(
          appBar: AppBar(title: const Text("Profile")),
          body: ListView(
            padding: const EdgeInsets.all(20),
            children: [
              CircleAvatar(
                radius: 50,
                backgroundImage: NetworkImage(userProfileStore.avatarUrl),
              ),
              const SizedBox(height: 12),
              Text(
                userProfileStore.name,
                style: const TextStyle(
                  fontSize: 20,
                  fontWeight: FontWeight.bold,
                ),
                textAlign: TextAlign.center,
              ),
              Text(
                userProfileStore.email,
                style: const TextStyle(color: Colors.grey),
                textAlign: TextAlign.center,
              ),
              const Divider(height: 32),

              ListTile(
                leading: const Icon(Icons.person),
                title: const Text("Account Settings"),
                trailing: const Icon(Icons.arrow_forward_ios, size: 16),
                onTap: () => Navigator.push(
                  context,
                  MaterialPageRoute(
                    builder: (_) => const AccountSettingsPage(),
                  ),
                ),
              ),
              ListTile(
                leading: const Icon(Icons.edit),
                title: const Text("Edit Account"),
                trailing: const Icon(Icons.arrow_forward_ios, size: 16),
                onTap: () => Navigator.push(
                  context,
                  MaterialPageRoute(builder: (_) => const EditAccountPage()),
                ),
              ),
              ListTile(
                leading: const Icon(Icons.favorite),
                title: const Text("Health Profile"),
                trailing: const Icon(Icons.arrow_forward_ios, size: 16),
                onTap: () => Navigator.push(
                  context,
                  MaterialPageRoute(builder: (_) => const HealthProfilePage()),
                ),
              ),
              SwitchListTile(
                secondary: const Icon(Icons.dark_mode),
                title: const Text("Dark Mode"),
                value: _darkMode,
                onChanged: (v) => setState(() => _darkMode = v),
              ),
              ListTile(
                leading: const Icon(Icons.logout, color: Colors.red),
                title: const Text(
                  "Logout",
                  style: TextStyle(color: Colors.red),
                ),
                onTap: () => _logout(context),
              ),
            ],
          ),
        );
      },
    );
  }
}

class AccountSettingsPage extends StatelessWidget {
  const AccountSettingsPage({super.key});

  @override
  Widget build(BuildContext context) {
    return AnimatedBuilder(
      animation: userProfileStore,
      builder: (context, _) {
        return Scaffold(
          appBar: AppBar(
            title: const Text("Account Settings"),
            actions: [
              IconButton(
                icon: const Icon(Icons.edit),
                onPressed: () => Navigator.push(
                  context,
                  MaterialPageRoute(builder: (_) => const EditAccountPage()),
                ),
              ),
            ],
          ),
          body: ListView(
            padding: const EdgeInsets.all(16),
            children: [
              ListTile(
                title: const Text("Name"),
                subtitle: Text(userProfileStore.name),
              ),
              ListTile(
                title: const Text("Email"),
                subtitle: Text(userProfileStore.email),
              ),
              ListTile(
                title: const Text("Phone"),
                subtitle: Text(userProfileStore.phone),
              ),
            ],
          ),
        );
      },
    );
  }
}

class EditAccountPage extends StatefulWidget {
  const EditAccountPage({super.key});
  @override
  State<EditAccountPage> createState() => _EditAccountPageState();
}

class _EditAccountPageState extends State<EditAccountPage> {
  late final TextEditingController _name = TextEditingController(
    text: userProfileStore.name,
  );
  late final TextEditingController _email = TextEditingController(
    text: userProfileStore.email,
  );
  late final TextEditingController _phone = TextEditingController(
    text: userProfileStore.phone,
  );
  late final TextEditingController _avatar = TextEditingController(
    text: userProfileStore.avatarUrl,
  );

  final _formKey = GlobalKey<FormState>();

  @override
  void dispose() {
    _name.dispose();
    _email.dispose();
    _phone.dispose();
    _avatar.dispose();
    super.dispose();
  }

  void _save() {
    if (_formKey.currentState?.validate() ?? false) {
      userProfileStore.update(
        name: _name.text.trim(),
        email: _email.text.trim(),
        phone: _phone.text.trim(),
        avatarUrl: _avatar.text.trim().isEmpty
            ? userProfileStore.avatarUrl
            : _avatar.text.trim(),
      );
      ScaffoldMessenger.of(
        context,
      ).showSnackBar(const SnackBar(content: Text("✅ Profile updated")));
      Navigator.pop(context);
    }
  }

  String? _req(String? v) =>
      (v == null || v.trim().isEmpty) ? "Required" : null;

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text("Edit Account"),
        actions: [
          TextButton(
            onPressed: _save,
            child: const Text("Save", style: TextStyle(color: Colors.white)),
          ),
        ],
      ),
      body: ListView(
        padding: const EdgeInsets.all(16),
        children: [
          Form(
            key: _formKey,
            child: Column(
              children: [
                TextFormField(
                  controller: _name,
                  decoration: const InputDecoration(labelText: "Name"),
                  validator: _req,
                ),
                const SizedBox(height: 12),
                TextFormField(
                  controller: _email,
                  decoration: const InputDecoration(labelText: "Email"),
                  validator: (v) {
                    if (_req(v) != null) return "Required";
                    if (!(v!.contains("@") && v.contains(".")))
                      return "Enter a valid email";
                    return null;
                  },
                  keyboardType: TextInputType.emailAddress,
                ),
                const SizedBox(height: 12),
                TextFormField(
                  controller: _phone,
                  decoration: const InputDecoration(labelText: "Phone"),
                  validator: _req,
                  keyboardType: TextInputType.phone,
                ),
                const SizedBox(height: 12),
                TextFormField(
                  controller: _avatar,
                  decoration: const InputDecoration(
                    labelText: "Avatar URL (optional)",
                  ),
                  keyboardType: TextInputType.url,
                ),
                const SizedBox(height: 24),
                SizedBox(
                  width: double.infinity,
                  child: ElevatedButton.icon(
                    onPressed: _save,
                    icon: const Icon(Icons.save),
                    label: const Text("Save Changes"),
                    style: ElevatedButton.styleFrom(
                      backgroundColor: Colors.blueAccent,
                      padding: const EdgeInsets.symmetric(vertical: 14),
                      shape: RoundedRectangleBorder(
                        borderRadius: BorderRadius.circular(12),
                      ),
                    ),
                  ),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}

class HealthProfilePage extends StatelessWidget {
  const HealthProfilePage({super.key});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text("Health Profile")),
      body: ListView(
        padding: const EdgeInsets.all(16),
        children: const [
          ListTile(title: Text("Age"), subtitle: Text("21")),
          ListTile(title: Text("Gender"), subtitle: Text("Male")),
          ListTile(title: Text("Blood Group"), subtitle: Text("B+")),
          ListTile(title: Text("Height"), subtitle: Text("5'11\"")),
          ListTile(title: Text("Weight"), subtitle: Text("72 kg")),
          ListTile(title: Text("Allergies"), subtitle: Text("None")),
        ],
      ),
    );
  }
}

/// =====================================================================
/// 🧱 Reusable widgets
/// =====================================================================
class _SuggestionCard extends StatelessWidget {
  final IconData icon;
  final String title;
  final VoidCallback? onTap;
  const _SuggestionCard({required this.icon, required this.title, this.onTap});

  @override
  Widget build(BuildContext context) {
    return Material(
      color: Colors.white,
      borderRadius: BorderRadius.circular(16),
      elevation: 2,
      child: InkWell(
        onTap: onTap,
        borderRadius: BorderRadius.circular(16),
        child: Container(
          decoration: BoxDecoration(borderRadius: BorderRadius.circular(16)),
          padding: const EdgeInsets.all(16),
          child: Column(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              Icon(icon, color: Colors.blue, size: 40),
              const SizedBox(height: 8),
              Text(
                title,
                textAlign: TextAlign.center,
                style: const TextStyle(fontWeight: FontWeight.w600),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

class _HomeAppointmentTile extends StatelessWidget {
  final Map<String, dynamic> doctor;
  final VoidCallback onTap;
  const _HomeAppointmentTile({required this.doctor, required this.onTap});

  @override
  Widget build(BuildContext context) {
    return Card(
      margin: const EdgeInsets.symmetric(vertical: 6),
      child: ListTile(
        leading: CircleAvatar(
          backgroundImage: NetworkImage(doctor["image"] as String),
        ),
        title: Text(
          doctor["name"] as String,
          style: const TextStyle(fontWeight: FontWeight.w600),
        ),
        subtitle: Text("${doctor["speciality"]} • ${doctor["country"]}"),
        trailing: const Icon(Icons.arrow_forward_ios, size: 16),
        onTap: onTap,
      ),
    );
  }
}

/// =====================================================================
/// 💎 Subscription UI (renamed to avoid conflicts)
/// =====================================================================
class PlanBanner extends StatelessWidget {
  const PlanBanner({super.key});

  @override
  Widget build(BuildContext context) {
    return AnimatedBuilder(
      animation: planStore,
      builder: (context, _) {
        return GestureDetector(
          onTap: () async {
            final result = await Navigator.push<String>(
              context,
              MaterialPageRoute(
                builder: (_) =>
                    PlanSubscriptionPage(currentPlan: planStore.currentPlan),
              ),
            );
            if (result != null && result.isNotEmpty) {
              planStore.updatePlan(result);
              // ignore: use_build_context_synchronously
              ScaffoldMessenger.of(context).showSnackBar(
                SnackBar(
                  content: Text("✅ Plan updated to ${planStore.currentPlan}"),
                ),
              );
            }
          },
          child: Container(
            padding: const EdgeInsets.all(16),
            decoration: BoxDecoration(
              color: Colors.purple[50],
              borderRadius: BorderRadius.circular(12),
              border: Border.all(color: Colors.purpleAccent, width: 1),
            ),
            child: Row(
              children: [
                const Icon(Icons.workspace_premium, color: Colors.purpleAccent),
                const SizedBox(width: 12),
                Expanded(
                  child: Text(
                    "Current Plan: ${planStore.currentPlan}\nTap to view or upgrade subscription",
                    style: const TextStyle(fontSize: 14, height: 1.4),
                  ),
                ),
                const Icon(
                  Icons.arrow_forward_ios,
                  size: 16,
                  color: Colors.purpleAccent,
                ),
              ],
            ),
          ),
        );
      },
    );
  }
}

class PlanSubscriptionPage extends StatelessWidget {
  final String currentPlan;
  const PlanSubscriptionPage({super.key, required this.currentPlan});

  @override
  Widget build(BuildContext context) {
    final List<Map<String, dynamic>> plans = [
      {
        "name": "Free",
        "price": "₹0",
        "note": "3 AI scans per day",
        "benefits": <String>[
          "3 AI scans per day",
          "Basic support",
          "Standard appointments",
        ],
      },
      {
        "name": "Pro",
        "price": "₹199",
        "note": "20 AI scans/day (30 days)",
        "benefits": <String>[
          "20 AI scans/day for 30 days",
          "Priority support",
          "Faster bookings",
        ],
      },
      {
        "name": "Premium",
        "price": "₹399",
        "note": "Unlimited scans/day (30 days)",
        "benefits": <String>[
          "Unlimited AI scans (30 days)",
          "24/7 premium support",
          "Fastest doctor appointments",
        ],
      },
    ];

    return Scaffold(
      appBar: AppBar(
        title: const Text("Subscription Plans"),
        backgroundColor: Colors.blueAccent,
      ),
      body: ListView(
        padding: const EdgeInsets.all(16),
        children: [
          const Text(
            "Choose the best plan for you 💎",
            style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold),
          ),
          const SizedBox(height: 20),
          ...plans.map((plan) {
            final bool isCurrent = plan["name"] == currentPlan;
            final List<String> benefits = (plan["benefits"] as List<dynamic>)
                .map((e) => e.toString())
                .toList();

            return Card(
              shape: RoundedRectangleBorder(
                borderRadius: BorderRadius.circular(12),
              ),
              elevation: 3,
              color: isCurrent ? Colors.blue[50] : Colors.white,
              margin: const EdgeInsets.only(bottom: 16),
              child: Padding(
                padding: const EdgeInsets.all(16),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Row(
                      mainAxisAlignment: MainAxisAlignment.spaceBetween,
                      children: [
                        Text(
                          plan["name"] as String,
                          style: const TextStyle(
                            fontSize: 20,
                            fontWeight: FontWeight.bold,
                          ),
                        ),
                        Column(
                          crossAxisAlignment: CrossAxisAlignment.end,
                          children: [
                            Text(
                              plan["price"] as String,
                              style: const TextStyle(
                                fontSize: 18,
                                color: Colors.blueAccent,
                                fontWeight: FontWeight.w700,
                              ),
                            ),
                            Text(
                              plan["note"] as String,
                              style: const TextStyle(
                                fontSize: 12,
                                color: Colors.grey,
                              ),
                            ),
                          ],
                        ),
                      ],
                    ),
                    const SizedBox(height: 8),
                    ...benefits.map(
                      (b) => Padding(
                        padding: const EdgeInsets.only(bottom: 4),
                        child: Row(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            const Icon(
                              Icons.check_circle,
                              size: 18,
                              color: Colors.green,
                            ),
                            const SizedBox(width: 6),
                            Expanded(child: Text(b)),
                          ],
                        ),
                      ),
                    ),
                    const SizedBox(height: 12),
                    SizedBox(
                      width: double.infinity,
                      child: ElevatedButton(
                        onPressed: isCurrent
                            ? null
                            : () => Navigator.pop(
                                context,
                                plan["name"] as String,
                              ),
                        style: ElevatedButton.styleFrom(
                          backgroundColor: Colors.blueAccent,
                          padding: const EdgeInsets.symmetric(vertical: 12),
                          shape: RoundedRectangleBorder(
                            borderRadius: BorderRadius.circular(12),
                          ),
                        ),
                        child: Text(
                          isCurrent ? "Current Plan" : "Choose ${plan["name"]}",
                        ),
                      ),
                    ),
                  ],
                ),
              ),
            );
          }),
        ],
      ),
    );
  }
}
