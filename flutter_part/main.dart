import 'dart:convert';
import 'package:flutter/material.dart';
import 'package:http/http.dart' as http;
import 'package:socket_io_client/socket_io_client.dart' as IO;

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
        colorScheme: ColorScheme.fromSeed(seedColor: Color(0xFF9E7C4E)), // Soft brown color
        useMaterial3: true,
        textTheme: TextTheme(
          headline1: TextStyle(fontFamily: 'Roboto', fontSize: 30, fontWeight: FontWeight.w600, color: Colors.brown[800]),
          bodyText1: TextStyle(fontFamily: 'Roboto', fontSize: 16, color: Colors.brown[700]),
          bodyText2: TextStyle(fontFamily: 'Roboto', fontSize: 14, color: Colors.brown[600]),
        ),
        elevatedButtonTheme: ElevatedButtonThemeData(
          style: ButtonStyle(
            backgroundColor: MaterialStateProperty.all(Colors.brown[200]),
            shape: MaterialStateProperty.all(RoundedRectangleBorder(borderRadius: BorderRadius.circular(12))),
          ),
        ),
      ),
      home: const MyHomePage(title: 'test_POS'),
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
  late IO.Socket socket;
  int? selectedTableId;
  List<Map<String, dynamic>> tables = [];

  @override
  void initState() {
    super.initState();
    fetchTables();
    initializeSocket();
  }

  void initializeSocket() {
    socket = IO.io('http://192.168.161.247:5000', <String, dynamic>{
      'transports': ['websocket'],
    });

    socket.on('connect', (_) {
      print('Connected to server');
    });

    socket.on('disconnect', (_) {
      print('Disconnected from server');
    });

    socket.on('table_freed', (data) {
      print('Table Freed: $data');
      setState(() {
        int tableId = int.parse(data['table_id'].toString());
        int index = tables.indexWhere((t) => t['id'] == tableId);
        if (index != -1) {
          tables[index]['status'] = 'Available';
        }
      });
    });

    socket.on('new_order', (data) {
      print('New Order: $data');
      setState(() {
        int tableId = int.parse(data['table_id'].toString());
        int index = tables.indexWhere((t) => t['id'] == tableId);
        if (index != -1) {
          tables[index]['status'] = 'Occupied';
        }
      });
    });
  }

  Future<void> fetchTables() async {
    final response = await http.get(Uri.parse('http://192.168.161.247:5000/flutter_api/tables'));
    if (response.statusCode == 200) {
      setState(() {
        tables = List<Map<String, dynamic>>.from(json.decode(response.body));
      });
    } else {
      print('Failed to load tables');
    }
  }

  void _selectTable(int tableId) {
    setState(() {
      selectedTableId = tableId;
    });
  }

  void _openOrderMenu(int tableId) async {
    final shouldRefresh = await Navigator.push(
      context,
      MaterialPageRoute(
        builder: (context) => OrderScreen(tableId: tableId),
      ),
    );

    // If order was submitted, refresh tables
    if (shouldRefresh == true) {
      fetchTables();
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: Text(widget.title),
        backgroundColor: Color(0xFF9E7C4E), // Soft brown color
        elevation: 6,
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.vertical(bottom: Radius.circular(20))),
      ),
      body: Column(
        children: [
          if (selectedTableId != null)
            Padding(
              padding: const EdgeInsets.all(16.0),
              child: Row(
                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                children: [
                  Text(
                    'Selected Table: $selectedTableId',
                    style: Theme.of(context).textTheme.headline1,
                  ),
                  ElevatedButton(
                    onPressed: () => _openOrderMenu(selectedTableId!),
                    child: const Text('Order'),
                  ),
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
                  child: Container(
                    decoration: BoxDecoration(
                      color: table['status'] == 'Occupied' ? Colors.red : Color(0xFF8E735B), // Earthy brown color
                      borderRadius: BorderRadius.circular(12),
                      boxShadow: [
                        BoxShadow(color: Colors.black26, blurRadius: 8, offset: Offset(0, 4))
                      ],
                    ),
                    alignment: Alignment.center,
                    child: Text(
                      'Table ${table['number']}',
                      style: TextStyle(
                        color: Colors.white,
                        fontSize: 18,
                        fontWeight: FontWeight.w500,
                      ),
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
  const OrderScreen({super.key, required this.tableId});

  @override
  State<OrderScreen> createState() => _OrderScreenState();
}

class _OrderScreenState extends State<OrderScreen> {
  Map<String, List<Map<String, dynamic>>> menu = {};
  List<int> selectedItemIds = [];

  @override
  void initState() {
    super.initState();
    fetchMenu();
  }

  Future<void> fetchMenu() async {
    final response = await http.get(Uri.parse('http://192.168.161.247:5000/flutter_api/menu'));
    if (response.statusCode == 200) {
      setState(() {
        menu = Map<String, List<Map<String, dynamic>>>.from(
          (json.decode(response.body) as Map).map(
            (key, value) => MapEntry(
              key,
              List<Map<String, dynamic>>.from(value),
            ),
          ),
        );
      });
    } else {
      print('Failed to load menu');
    }
  }

  void _submitOrder() async {
    final response = await http.post(
      Uri.parse('http://192.168.161.247:5000/flutter_api/order'),
      headers: {'Content-Type': 'application/json'},
      body: json.encode({
        'table_id': widget.tableId,
        'items': selectedItemIds,
      }),
    );

    if (response.statusCode == 200) {
      setState(() {
        selectedItemIds.clear();
      });

      // Pop and pass back a flag to refresh
      Navigator.pop(context, true);
    } else {
      print('Failed to submit order');
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: Text('Order for Table ${widget.tableId}'),
        backgroundColor: Color(0xFF9E7C4E), // Soft brown color
        elevation: 6,
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.vertical(bottom: Radius.circular(20))),
      ),
      body: Column(
        children: [
          Expanded(
            child: ListView(
              children: menu.entries.map((entry) {
                return Container(
                  color: Colors.brown[50], // Lighter background for categories
                  child: ExpansionTile(
                    title: Text(entry.key, style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold, color: Colors.brown[700])),
                    children: entry.value.map((item) {
                      return ListTile(
                        title: Text(item['name']),
                        trailing: IconButton(
                          icon: const Icon(Icons.add),
                          onPressed: () {
                            setState(() {
                              selectedItemIds.add(item['id']);
                            });
                          },
                        ),
                      );
                    }).toList(),
                  ),
                );
              }).toList(),
            ),
          ),
          Container(
            color: Colors.brown[50],
            padding: const EdgeInsets.all(8.0),
            child: Column(
              children: [
                const Text(
                  'Selected Items:',
                  style: TextStyle(fontWeight: FontWeight.bold),
                ),
                Wrap(
                  spacing: 8.0,
                  children: selectedItemIds.map((id) {
                    final item = menu.entries
                        .expand((e) => e.value)
                        .firstWhere((element) => element['id'] == id);
                    return Chip(
                      label: Text(item['name']),
                      onDeleted: () {
                        setState(() {
                          selectedItemIds.remove(id);
                        });
                      },
                    );
                  }).toList(),
                ),
                ElevatedButton(
                  onPressed: _submitOrder,
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

