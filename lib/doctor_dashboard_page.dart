import 'dart:io';
import 'package:flutter/material.dart';
import 'package:image_picker/image_picker.dart';
import 'package:shared_preferences/shared_preferences.dart';

class DoctorDashboardPage extends StatefulWidget {
  const DoctorDashboardPage({super.key});

  @override
  State<DoctorDashboardPage> createState() => _DoctorDashboardPageState();
}

class _DoctorDashboardPageState extends State<DoctorDashboardPage> {
  bool _darkMode = false;
  String _currentPlan = "Free";

  // 👨‍⚕️ Doctor Info
  String _name = "Dr. Arjun Singh";
  String _speciality = "General Physician";
  String _experience = "10+ Years";
  String _email = "dr.arjun@example.com";
  String _clinic = "HealthyLife Clinic, Connaught Place, New Delhi";
  String _bio =
      "Renowned general physician with 10+ years of experience in lifestyle and chronic disease management.";
  String _photoUrl = "https://i.pravatar.cc/150?img=9";

  final List<Map<String, String>> _appointments = [
    {"name": "Aman Sharma", "time": "10:00 AM", "date": "29 Sept 2025", "type": "Online"},
    {"name": "Priya Verma", "time": "12:30 PM", "date": "29 Sept 2025", "type": "In-Person"},
  ];

  final List<Map<String, String>> _patients = [
    {"name": "Ravi Kumar", "lastVisit": "15 Sept 2025"},
    {"name": "Neha Gupta", "lastVisit": "21 Sept 2025"},
  ];

  @override
  void initState() {
    super.initState();
    _loadDoctorInfo();
  }

  Future<void> _loadDoctorInfo() async {
    final prefs = await SharedPreferences.getInstance();
    setState(() {
      _name = prefs.getString('doctor_name') ?? _name;
      _speciality = prefs.getString('doctor_speciality') ?? _speciality;
      _experience = prefs.getString('doctor_experience') ?? _experience;
      _email = prefs.getString('doctor_email') ?? _email;
      _clinic = prefs.getString('doctor_clinic') ?? _clinic;
      _bio = prefs.getString('doctor_bio') ?? _bio;
      _photoUrl = prefs.getString('doctor_photo') ?? _photoUrl;
      _currentPlan = prefs.getString('doctor_plan') ?? _currentPlan;
    });
  }

  Future<void> _saveDoctorInfo() async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.setString('doctor_name', _name);
    await prefs.setString('doctor_speciality', _speciality);
    await prefs.setString('doctor_experience', _experience);
    await prefs.setString('doctor_email', _email);
    await prefs.setString('doctor_clinic', _clinic);
    await prefs.setString('doctor_bio', _bio);
    await prefs.setString('doctor_photo', _photoUrl);
    await prefs.setString('doctor_plan', _currentPlan);
  }

  void _logout() {
    showDialog(
      context: context,
      builder: (_) => AlertDialog(
        title: const Text("Logout"),
        content: const Text("Are you sure you want to logout?"),
        actions: [
          TextButton(onPressed: () => Navigator.pop(context), child: const Text("Cancel")),
          TextButton(
            onPressed: () {
              Navigator.pop(context);
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

  void _openSubscriptionPage() {
    Navigator.push(
      context,
      MaterialPageRoute(
        builder: (_) => SubscriptionPage(
          currentPlan: _currentPlan,
          onPlanSelected: (String plan) {
            setState(() => _currentPlan = plan);
            _saveDoctorInfo();
          },
        ),
      ),
    );
  }

  void _openProfilePage() {
    Navigator.push(
      context,
      MaterialPageRoute(
        builder: (_) => DoctorProfilePage(
          name: _name,
          speciality: _speciality,
          experience: _experience,
          email: _email,
          clinic: _clinic,
          bio: _bio,
          photoUrl: _photoUrl,
          onSave: (updatedData) {
            setState(() {
              _name = updatedData["name"]!;
              _speciality = updatedData["speciality"]!;
              _experience = updatedData["experience"]!;
              _email = updatedData["email"]!;
              _clinic = updatedData["clinic"]!;
              _bio = updatedData["bio"]!;
              _photoUrl = updatedData["photoUrl"]!;
            });
            _saveDoctorInfo();
          },
        ),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final bool isDark = _darkMode;
    return Scaffold(
      backgroundColor: isDark ? Colors.black : Colors.white,
      appBar: AppBar(
        title: const Text("Doctor Dashboard"),
        backgroundColor: Colors.blueAccent,
        actions: [
          IconButton(
            icon: Icon(isDark ? Icons.light_mode : Icons.dark_mode, color: Colors.white),
            onPressed: () => setState(() => _darkMode = !_darkMode),
          ),
        ],
      ),
      body: Padding(
        padding: const EdgeInsets.all(16.0),
        child: ListView(
          children: [
            Column(
              children: [
                CircleAvatar(
                  radius: 50,
                  backgroundImage: _photoUrl.startsWith('http')
                      ? NetworkImage(_photoUrl)
                      : FileImage(File(_photoUrl)) as ImageProvider,
                ),
                const SizedBox(height: 12),
                Text(
                  "Welcome, $_name 👨‍⚕️",
                  style: TextStyle(
                    fontSize: 22,
                    fontWeight: FontWeight.bold,
                    color: isDark ? Colors.white : Colors.black,
                  ),
                ),
                Text("$_speciality | $_experience Exp.",
                    style: TextStyle(color: isDark ? Colors.grey : Colors.black54)),
                const SizedBox(height: 6),
                Chip(
                  label: Text("Plan: $_currentPlan"),
                  backgroundColor: Colors.blueAccent.withOpacity(0.2),
                  avatar: const Icon(Icons.workspace_premium, color: Colors.blueAccent),
                ),
              ],
            ),
            const SizedBox(height: 24),

            // 🏥 Clinic Info
            Card(
              color: isDark ? Colors.blueGrey[900] : Colors.blue[50],
              shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
              child: ListTile(
                leading: const Icon(Icons.local_hospital, color: Colors.blueAccent),
                title: Text(_clinic, style: const TextStyle(fontWeight: FontWeight.w600)),
                subtitle: Text(_email),
                trailing: const Icon(Icons.edit, color: Colors.blueAccent),
                onTap: _openProfilePage,
              ),
            ),

            const SizedBox(height: 24),
            Text("Upcoming Appointments",
                style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold, color: isDark ? Colors.white : Colors.black)),
            const SizedBox(height: 12),
            ..._appointments.map((a) => Card(
                  child: ListTile(
                    leading: const Icon(Icons.person, color: Colors.blueAccent),
                    title: Text(a["name"] ?? ""),
                    subtitle: Text("${a["date"]} • ${a["time"]} • ${a["type"]}"),
                  ),
                )),

            const SizedBox(height: 24),
            Text("My Patients",
                style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold, color: isDark ? Colors.white : Colors.black)),
            const SizedBox(height: 12),
            ..._patients.map((p) => Card(
                  child: ListTile(
                    leading: const Icon(Icons.people_alt, color: Colors.green),
                    title: Text(p["name"] ?? ""),
                    subtitle: Text("Last Visit: ${p["lastVisit"]}"),
                  ),
                )),

            const SizedBox(height: 24),
            Card(
              child: Column(
                children: [
                  ListTile(
                    leading: const Icon(Icons.person),
                    title: const Text("My Profile"),
                    onTap: _openProfilePage,
                  ),
                  ListTile(
                    leading: const Icon(Icons.settings),
                    title: const Text("Subscription & Settings"),
                    onTap: _openSubscriptionPage,
                  ),
                ],
              ),
            ),
            const SizedBox(height: 40),
            ElevatedButton.icon(
              icon: const Icon(Icons.logout),
              label: const Text("Logout"),
              onPressed: _logout,
              style: ElevatedButton.styleFrom(
                backgroundColor: Colors.redAccent,
                padding: const EdgeInsets.symmetric(vertical: 16),
                shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
              ),
            ),
          ],
        ),
      ),
    );
  }
}

//
// 👤 Doctor Profile Page (Editable)
//
class DoctorProfilePage extends StatefulWidget {
  final String name, speciality, experience, email, clinic, bio, photoUrl;
  final Function(Map<String, String>) onSave;

  const DoctorProfilePage({
    super.key,
    required this.name,
    required this.speciality,
    required this.experience,
    required this.email,
    required this.clinic,
    required this.bio,
    required this.photoUrl,
    required this.onSave,
  });

  @override
  State<DoctorProfilePage> createState() => _DoctorProfilePageState();
}

class _DoctorProfilePageState extends State<DoctorProfilePage> {
  late TextEditingController _nameCtrl;
  late TextEditingController _specialityCtrl;
  late TextEditingController _experienceCtrl;
  late TextEditingController _emailCtrl;
  late TextEditingController _clinicCtrl;
  late TextEditingController _bioCtrl;
  late TextEditingController _photoCtrl;
  final ImagePicker _picker = ImagePicker();

  @override
  void initState() {
    super.initState();
    _nameCtrl = TextEditingController(text: widget.name);
    _specialityCtrl = TextEditingController(text: widget.speciality);
    _experienceCtrl = TextEditingController(text: widget.experience);
    _emailCtrl = TextEditingController(text: widget.email);
    _clinicCtrl = TextEditingController(text: widget.clinic);
    _bioCtrl = TextEditingController(text: widget.bio);
    _photoCtrl = TextEditingController(text: widget.photoUrl);
  }

  Future<void> _pickImage() async {
    final picked = await _picker.pickImage(source: ImageSource.gallery);
    if (picked != null) {
      setState(() => _photoCtrl.text = picked.path);
    }
  }

  @override
  Widget build(BuildContext context) {
    final bool isNetwork = _photoCtrl.text.startsWith('http');
    return Scaffold(
      appBar: AppBar(title: const Text("Edit Profile")),
      body: Padding(
        padding: const EdgeInsets.all(16),
        child: ListView(
          children: [
            Center(
              child: CircleAvatar(
                radius: 50,
                backgroundImage:
                    isNetwork ? NetworkImage(_photoCtrl.text) : FileImage(File(_photoCtrl.text)) as ImageProvider,
              ),
            ),
            TextButton(onPressed: _pickImage, child: const Text("Change Photo")),
            const SizedBox(height: 12),
            _buildField("Full Name", _nameCtrl),
            _buildField("Speciality", _specialityCtrl),
            _buildField("Experience", _experienceCtrl),
            _buildField("Email", _emailCtrl),
            _buildField("Clinic Name / Address", _clinicCtrl),
            _buildField("Short Bio", _bioCtrl, maxLines: 3),
            const SizedBox(height: 24),
            ElevatedButton.icon(
              icon: const Icon(Icons.save),
              label: const Text("Save Changes"),
              style: ElevatedButton.styleFrom(
                backgroundColor: Colors.blueAccent,
                padding: const EdgeInsets.symmetric(vertical: 14),
                shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
              ),
              onPressed: () {
                widget.onSave({
                  "name": _nameCtrl.text,
                  "speciality": _specialityCtrl.text,
                  "experience": _experienceCtrl.text,
                  "email": _emailCtrl.text,
                  "clinic": _clinicCtrl.text,
                  "bio": _bioCtrl.text,
                  "photoUrl": _photoCtrl.text,
                });
                Navigator.pop(context);
                ScaffoldMessenger.of(context)
                    .showSnackBar(const SnackBar(content: Text("✅ Profile updated successfully!")));
              },
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildField(String label, TextEditingController ctrl, {int maxLines = 1}) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 12),
      child: TextField(
        controller: ctrl,
        maxLines: maxLines,
        decoration: InputDecoration(labelText: label, border: const OutlineInputBorder()),
      ),
    );
  }
}

//
// 💎 Subscription Page
//
class SubscriptionPage extends StatelessWidget {
  final String currentPlan;
  final ValueChanged<String> onPlanSelected;

  const SubscriptionPage({super.key, required this.currentPlan, required this.onPlanSelected});

  @override
  Widget build(BuildContext context) {
    final List<Map<String, dynamic>> plans = [
      {
        "name": "Free",
        "price": "₹0 / month",
        "reach": "Reach up to 100 patients/month",
        "features": ["Basic visibility", "Standard support", "Limited reach"]
      },
      {
        "name": "Pro",
        "price": "₹199 / month",
        "reach": "Reach up to 2,000 patients/month",
        "features": ["Priority listing", "Advanced analytics", "Direct chat with patients"]
      },
      {
        "name": "Premium",
        "price": "₹799 / month",
        "reach": "Reach up to 10,000 patients/month",
        "features": ["Top search ranking", "Unlimited appointments", "24/7 Premium Support"]
      },
    ];

    return Scaffold(
      appBar: AppBar(title: const Text("Upgrade Your Plan")),
      body: ListView(
        padding: const EdgeInsets.all(16),
        children: [
          const Text("Choose your subscription plan 💼",
              style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold)),
          const SizedBox(height: 20),
          ...plans.map((plan) {
            final bool isSelected = plan["name"] == currentPlan;
            final List features = plan["features"] as List;
            return Card(
              elevation: 4,
              color: isSelected ? Colors.blue[50] : Colors.white,
              shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
              child: Padding(
                padding: const EdgeInsets.all(16),
                child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                  Row(mainAxisAlignment: MainAxisAlignment.spaceBetween, children: [
                    Text(plan["name"], style: const TextStyle(fontSize: 20, fontWeight: FontWeight.bold)),
                    Text(plan["price"], style: const TextStyle(fontSize: 16, color: Colors.blueAccent)),
                  ]),
                  const SizedBox(height: 6),
                  Text(plan["reach"], style: const TextStyle(color: Colors.grey)),
                  const Divider(),
                  ...features.map((f) => Padding(
                        padding: const EdgeInsets.only(bottom: 4),
                        child: Row(children: [
                          const Icon(Icons.check_circle, color: Colors.green, size: 18),
                          const SizedBox(width: 6),
                          Text(f.toString()),
                        ]),
                      )),
                  const SizedBox(height: 10),
                  SizedBox(
                    width: double.infinity,
                    child: ElevatedButton(
                      onPressed: isSelected
                          ? null
                          : () {
                              onPlanSelected(plan["name"]);
                              Navigator.pop(context);
                              ScaffoldMessenger.of(context).showSnackBar(
                                SnackBar(content: Text("✅ ${plan["name"]} plan activated!")),
                              );
                            },
                      style: ElevatedButton.styleFrom(
                        backgroundColor: Colors.blueAccent,
                        padding: const EdgeInsets.symmetric(vertical: 14),
                        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
                      ),
                      child: Text(isSelected ? "Current Plan" : "Upgrade"),
                    ),
                  ),
                ]),
              ),
            );
          }),
        ],
      ),
    );
  }
}
