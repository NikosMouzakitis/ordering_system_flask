import 'dart:convert';
import 'package:flutter/material.dart';
import 'package:http/http.dart' as http;
import 'package:socket_io_client/socket_io_client.dart' as IO;
import 'package:shared_preferences/shared_preferences.dart';

void main() {
  runApp(const MyApp());
}

class MyApp extends StatelessWidget {
  const MyApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'Flutter POS',
      theme: ThemeData(
        colorScheme: ColorScheme.fromSeed(seedColor: const Color(0xFF9E7C4E)),
        useMaterial3: true,
      ),
      home: const IPConfigPage(),
    );
  }
}

class IPConfigPage extends StatefulWidget {
  const IPConfigPage({super.key});

  @override
  State<IPConfigPage> createState() => _IPConfigPageState();
}

class _IPConfigPageState extends State<IPConfigPage> {
  final TextEditingController _ipController = TextEditingController();

  Future<void> _saveIP() async {
    SharedPreferences prefs = await SharedPreferences.getInstance();
    await prefs.setString('server_ip', _ipController.text.trim());
    Navigator.pushReplacement(
        context, MaterialPageRoute(builder: (_) => const MyHomePage(title: 'POS')));
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Server Configuration')),
      body: Padding(
        padding: const EdgeInsets.all(16.0),
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            const Text('Enter Server IP:'),
            TextField(
              controller: _ipController,
              decoration: const InputDecoration(hintText: 'e.g., 192.168.1.100'),
            ),
            const SizedBox(height: 16),
            ElevatedButton(onPressed: _saveIP, child: const Text('Continue')),
          ],
        ),
      ),
    );
  }
}

class MyHomePage extends StatefulWidget {
  const MyHomePage({super.key, required this.title});
  final String title;

  @override
  State<MyHomePage> createState() => _MyHomePageState();
}

class _MyHomePageState extends State<MyHomePage> {
  OverlayEntry? _orderOverlayEntry;
  late IO.Socket socket;
  int? selectedTableId;
  List<Map<String, dynamic>> tables = [];
  String serverIp = '';

  @override
  void initState() {
    super.initState();
    _loadServerIP();
  }

  Future<void> _loadServerIP() async {
    SharedPreferences prefs = await SharedPreferences.getInstance();
    serverIp = prefs.getString('server_ip') ?? '';
    if (serverIp.isEmpty) {
      Navigator.pushReplacement(
          context, MaterialPageRoute(builder: (_) => const IPConfigPage()));
    } else {
      fetchTables();
      initializeSocket();
    }
  }

void _showOrderOverlay(BuildContext context, int tableId) async {
  try {
    final response = await http.get(Uri.parse('http://$serverIp:5000/flutter_api/get_orders/$tableId'));

    if (response.statusCode == 200) {
      final order = json.decode(response.body);

      // Ensure that we check if 'orders' exists and is a non-empty list
      if (order['orders'] != null && order['orders'].isNotEmpty) {
        _orderOverlayEntry = OverlayEntry(
          builder: (context) => Positioned(
            top: 100,
            left: 50,
            right: 50,
            child: Material(
              elevation: 10,
              color: Colors.white,
              borderRadius: BorderRadius.circular(12),
              child: Padding(
                padding: const EdgeInsets.all(16.0),
                child: Column(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    Text('Table $tableId Order', style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 18)),
                    const SizedBox(height: 10),
                    ...order['orders'].map<Widget>((item) => Text('- $item')).toList(),
                  ],
                ),
              ),
            ),
          ),
        );

        Overlay.of(context).insert(_orderOverlayEntry!);
      } else {
        // If no items, show a default message or handle it accordingly
        _orderOverlayEntry = OverlayEntry(
          builder: (context) => Positioned(
            top: 100,
            left: 50,
            right: 50,
            child: Material(
              elevation: 10,
              color: Colors.white,
              borderRadius: BorderRadius.circular(12),
              child: Padding(
                padding: const EdgeInsets.all(16.0),
                child: Column(
                  mainAxisSize: MainAxisSize.min,
                  children: const [
                    Text('Table has no active orders.', style: TextStyle(fontWeight: FontWeight.bold, fontSize: 18)),
                  ],
                ),
              ),
            ),
          ),
        );
        Overlay.of(context).insert(_orderOverlayEntry!);
      }
    }
  } catch (e) {
    print('Error fetching order: $e');
  }
}
 

  void _removeOrderOverlay() {
    _orderOverlayEntry?.remove();
    _orderOverlayEntry = null;
  }

  void initializeSocket() {
    socket = IO.io('http://$serverIp:5000', <String, dynamic>{
      'transports': ['websocket'],
    });

    socket.on('connect', (_) => print('Connected to server'));
    socket.on('disconnect', (_) => print('Disconnected from server'));

    socket.on('table_freed', (data) {
      int tableId = int.parse(data['table_id'].toString());
      int index = tables.indexWhere((t) => t['id'] == tableId);
      if (index != -1) setState(() => tables[index]['status'] = 'Available');
    });

    socket.on('new_order', (data) {
      int tableId = int.parse(data['table_id'].toString());
      int index = tables.indexWhere((t) => t['id'] == tableId);
      if (index != -1) setState(() => tables[index]['status'] = 'Occupied');
    });
  }

  Future<void> fetchTables() async {
    try {
      final response =
          await http.get(Uri.parse('http://$serverIp:5000/flutter_api/tables'));
      if (response.statusCode == 200) {
        setState(() => tables =
            List<Map<String, dynamic>>.from(json.decode(response.body)));
      }
    } catch (e) {
      print('Failed to load tables: $e');
    }
  }

  void _selectTable(int tableId) => setState(() => selectedTableId = tableId);

  void _openOrderMenu(int tableId) async {
    final shouldRefresh = await Navigator.push(
      context,
      MaterialPageRoute(
          builder: (context) =>
              OrderScreen(tableId: tableId, serverIp: serverIp)),
    );
    if (shouldRefresh == true) fetchTables();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: Text(widget.title),
        backgroundColor: const Color(0xFF9E7C4E),
        elevation: 6,
        shape: const RoundedRectangleBorder(
            borderRadius: BorderRadius.vertical(bottom: Radius.circular(20))),
      ),
      body: Column(
        children: [
          if (selectedTableId != null)
            Padding(
              padding: const EdgeInsets.all(16.0),
              child: Row(
                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                children: [
                  Text('Selected Table: $selectedTableId',
                      style: Theme.of(context).textTheme.headline6),
                  ElevatedButton(
                      onPressed: () => _openOrderMenu(selectedTableId!),
                      child: const Text('Order')),
                ],
              ),
            ),
          Expanded(
            child: GridView.builder(
              padding: const EdgeInsets.all(12),
              gridDelegate: const SliverGridDelegateWithFixedCrossAxisCount(
                crossAxisCount: 3,
                crossAxisSpacing: 10,
                mainAxisSpacing: 10,
                childAspectRatio: 1.2,
              ),
              itemCount: tables.length,
              itemBuilder: (context, index) {
                final table = tables[index];
                return GestureDetector(
                  onTap: () => _selectTable(table['id']),
                  onLongPressStart: (_) =>
                      _showOrderOverlay(context, table['id']),
                  onLongPressEnd: (_) => _removeOrderOverlay(),
                  child: Container(
                    decoration: BoxDecoration(
                      color: table['status'] == 'Occupied'
                          ? Colors.red
                          : const Color(0xFF8E735B),
                      borderRadius: BorderRadius.circular(12),
                      boxShadow: const [
                        BoxShadow(
                            color: Colors.black26,
                            blurRadius: 8,
                            offset: Offset(0, 4))
                      ],
                    ),
                    alignment: Alignment.center,
                    child: Text(
                      'Table ${table['number']}',
                      style: const TextStyle(
                          color: Colors.white,
                          fontSize: 18,
                          fontWeight: FontWeight.w500),
                    ),
                  ),
                );
              },
            ),
          ),
        ],
      ),
    );
  }
}

class OrderScreen extends StatefulWidget {
  final int tableId;
  final String serverIp;
  const OrderScreen({super.key, required this.tableId, required this.serverIp});

  @override
  State<OrderScreen> createState() => _OrderScreenState();
}

class _OrderScreenState extends State<OrderScreen> {
  Map<String, List<Map<String, dynamic>>> menu = {};
  Map<int, int> selectedItemCounts = {};

  @override
  void initState() {
    super.initState();
    fetchMenu();
  }

  Future<void> fetchMenu() async {
    try {
      final response =
          await http.get(Uri.parse('http://${widget.serverIp}:5000/flutter_api/menu'));
      if (response.statusCode == 200) {
        setState(() {
          menu = Map<String, List<Map<String, dynamic>>>.from(
            (json.decode(response.body) as Map).map(
              (key, value) =>
                  MapEntry(key, List<Map<String, dynamic>>.from(value)),
            ),
          );
        });
      }
    } catch (e) {
      print('Failed to load menu: $e');
    }
  }

  void _submitOrder() async {
    final filtered = selectedItemCounts.entries.where((e) => e.value > 0).toList();
    if (filtered.isEmpty) {
      ScaffoldMessenger.of(context)
          .showSnackBar(const SnackBar(content: Text('Please select at least one item')));
      return;
    }

    final List<int> flatItemIds = [];
    for (var entry in filtered) {
      flatItemIds.addAll(List.generate(entry.value, (_) => entry.key));
    }

    final response = await http.post(
      Uri.parse('http://${widget.serverIp}:5000/flutter_api/order'),
      headers: {'Content-Type': 'application/json'},
      body: json.encode({
        'table_id': widget.tableId,
        'items': flatItemIds,
      }),
    );

    if (response.statusCode == 200) {
      setState(() => selectedItemCounts.clear());
      ScaffoldMessenger.of(context)
          .showSnackBar(const SnackBar(content: Text('Order submitted')));
      Navigator.pop(context, true);
    } else {
      ScaffoldMessenger.of(context)
          .showSnackBar(const SnackBar(content: Text('Failed to submit order')));
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: Text('Order for Table ${widget.tableId}'),
        backgroundColor: const Color(0xFF9E7C4E),
      ),
      body: Column(
        children: [
          Expanded(
            child: ListView(
              children: menu.entries.map((entry) {
                return ExpansionTile(
                  title: Text(entry.key,
                      style: const TextStyle(
                          fontSize: 18, fontWeight: FontWeight.bold)),
                  children: entry.value.map((item) {
                    final itemId = item['id'];
                    final count = selectedItemCounts[itemId] ?? 0;
                    return ListTile(
                      title: Text(item['name']),
                      trailing: Row(
                        mainAxisSize: MainAxisSize.min,
                        children: [
                          IconButton(
                            onPressed: () {
                              if (count > 0) {
                                setState(() => selectedItemCounts[itemId] = count - 1);
                              }
                            },
                            icon: const Icon(Icons.remove),
                          ),
                          Text('$count'),
                          IconButton(
                            onPressed: () =>
                                setState(() => selectedItemCounts[itemId] = count + 1),
                            icon: const Icon(Icons.add),
                          ),
                        ],
                      ),
                    );
                  }).toList(),
                );
              }).toList(),
            ),
          ),
          Container(
            color: Colors.brown[50],
            padding: const EdgeInsets.all(8.0),
            child: Column(
              children: [
                const Text('Selected Items:',
                    style: TextStyle(fontWeight: FontWeight.bold)),
                Wrap(
                  spacing: 8.0,
                  children: selectedItemCounts.entries.map((entry) {
                    final item = menu.entries
                        .expand((e) => e.value)
                        .firstWhere((e) => e['id'] == entry.key);
                    return Chip(label: Text('${item['name']} x${entry.value}'));
                  }).toList(),
                ),
                ElevatedButton(
                  onPressed: selectedItemCounts.values.any((q) => q > 0)
                      ? _submitOrder
                      : null,
                  child: const Text('Submit Order'),
                ),
                ElevatedButton(
                  onPressed: () => Navigator.pop(context),
                  child: const Text('Back'),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}

