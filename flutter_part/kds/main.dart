import 'package:flutter/material.dart';
import 'package:http/http.dart' as http;
import 'package:socket_io_client/socket_io_client.dart' as IO;
import 'dart:convert';
import 'package:shared_preferences/shared_preferences.dart';

void main() async {
  WidgetsFlutterBinding.ensureInitialized();
  final prefs = await SharedPreferences.getInstance();
  final serverIp = prefs.getString('server_ip') ?? '';
  
  runApp(MaterialApp(
    home: serverIp.isEmpty ? const IPConfigPage() : KitchenScreen(serverIp: serverIp),
    debugShowCheckedModeBanner: false,
    theme: ThemeData(
      primarySwatch: Colors.orange,
      cardTheme: const CardTheme(
        elevation: 4,
        margin: EdgeInsets.all(8),
      ),
    ),
  ));
}

class IPConfigPage extends StatelessWidget {
  const IPConfigPage({super.key});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Server Configuration')),
      body: const Center(child: Text('IP Configuration would go here')),
    );
  }
}

class KitchenScreen extends StatefulWidget {
  final String serverIp;
  const KitchenScreen({super.key, required this.serverIp});

  @override
  State<KitchenScreen> createState() => _KitchenScreenState();
}

class _KitchenScreenState extends State<KitchenScreen> {
  late IO.Socket socket;
  List<dynamic> orders = [];
  bool isLoading = true;

  @override
  void initState() {
    super.initState();
    _connectToSocket();
    _fetchOrders();
  }


  void _connectToSocket() {

  print('Connecting to: http://${widget.serverIp}:5000');

  socket = IO.io(
    'http://${widget.serverIp}:5000',
    IO.OptionBuilder()
      .setTransports(['websocket'])
      .build(),
  );

  socket.onConnect((_) {
    print('Connected to KDS server');
  });

  // Listen for item completion events
  socket.on('new_order', (_) {
        print('New order received via socket');
        _fetchOrders();
      });

  socket.on('item_completed', (data) {
    print('Item completed: $data');
    _fetchOrders(); // Refresh orders
  });

  // Listen for order completion events
  socket.on('order_completed', (data) {
    print('Order completed: $data');
    _fetchOrders(); // Refresh orders
  });

  socket.connect();
}

  Future<void> _fetchOrders() async {
    try {
      final response = await http.get(
        Uri.parse('http://${widget.serverIp}:5000/api/kds/orders?station=kitchen'),
      );

      if (response.statusCode == 200) {
        final data = json.decode(response.body);
        setState(() {
          orders = List<dynamic>.from(data);
          isLoading = false;
        });
      } else {
        throw Exception('Failed to load orders');
      }
    } catch (e) {
      print('Error fetching orders: $e');
      setState(() => isLoading = false);
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('Error loading orders: $e')),
      );
    }
  }

 
Future<void> _completeItem(int orderId, int itemId, String itemName) async {
  try {
    // Optimistic UI update
    setState(() {
      final orderIndex = orders.indexWhere((o) => o['id'] == orderId);
      if (orderIndex != -1) {
        final itemIndex = orders[orderIndex]['items']
            .indexWhere((i) => i['id'] == itemId);
        if (itemIndex != -1) {
          orders[orderIndex]['items'][itemIndex]['completed'] = true;
        }
      }
    });

    final response = await http.post(
      Uri.parse('http://${widget.serverIp}:5000/api/kds/complete_item'),
      headers: {'Content-Type': 'application/json'},
      body: json.encode({
        'order_id': orderId,
        'item_id': itemId,
      }),
    );

    if (response.statusCode != 200) {
      // Revert if failed
      setState(() {
        final orderIndex = orders.indexWhere((o) => o['id'] == orderId);
        if (orderIndex != -1) {
          final itemIndex = orders[orderIndex]['items']
              .indexWhere((i) => i['id'] == itemId);
          if (itemIndex != -1) {
            orders[orderIndex]['items'][itemIndex]['completed'] = false;
          }
        }
      });
      throw Exception('Failed to complete item: ${response.body}');
    }

    // Force refresh from server
    _fetchOrders();

  } catch (e) {
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(content: Text('Error: $e')),
    );
  }
}





  Future<void> _completeOrder(int orderId) async {
    final order = orders.firstWhere((o) => o['id'] == orderId);
    final pendingItems = order['items'].where((i) => !i['completed']).toList();

    if (pendingItems.isNotEmpty) {
      final confirm = await showDialog<bool>(
        context: context,
        builder: (context) => AlertDialog(
          title: const Text('Complete Order?'),
          content: Text('There are ${pendingItems.length} items not marked as prepared. '
              'Complete the entire order anyway?'),
          actions: [
            TextButton(
              onPressed: () => Navigator.pop(context, false),
              child: const Text('Cancel'),
            ),
            TextButton(
              onPressed: () => Navigator.pop(context, true),
              child: const Text('Complete'),
            ),
          ],
        ),
      );
      if (confirm != true) return;
    }

    try {
      final response = await http.post(
        Uri.parse('http://${widget.serverIp}:5000/api/kds/complete'),
        headers: {'Content-Type': 'application/json'},
        body: json.encode({'order_id': orderId}),
      );

      if (response.statusCode != 200) {
        throw Exception('Failed to complete order');
      }
    } catch (e) {
      print('Error completing order: $e');
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('Failed to complete order: $e')),
      );
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Kitchen Display'),
        actions: [
          IconButton(
            icon: const Icon(Icons.refresh),
            onPressed: _fetchOrders,
          ),
        ],
      ),
      body: isLoading
          ? const Center(child: CircularProgressIndicator())
          : orders.isEmpty
              ? const Center(child: Text('No pending orders'))
              : ListView.builder(
                  itemCount: orders.length,
                  itemBuilder: (context, index) {
                    final order = orders[index];
                    final allItemsCompleted = order['items']
                        .every((item) => item['completed'] == true);

                    return Card(
                      margin: const EdgeInsets.all(8),
                      child: Padding(
                        padding: const EdgeInsets.all(12),
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Row(
                              mainAxisAlignment: MainAxisAlignment.spaceBetween,
                              children: [
                                Text(
                                  'Table ${order['table_id']}',
                                  style: const TextStyle(
                                    fontWeight: FontWeight.bold,
                                    fontSize: 18,
                                  ),
                                ),
                                Text(
                                  'Waiting: ${order['wait_time']}',
                                  style: TextStyle(
                                    color: Colors.grey[600],
                                  ),
                                ),
                              ],
                            ),
                            const Divider(),
                            ...order['items'].map<Widget>((item) {
                              return ListTile(
                                leading: item['completed'] == true
                                    ? const Icon(Icons.check_circle, color: Colors.green)
                                    : null,
                                title: Text(
                                  item['name'],
                                  style: TextStyle(
                                    decoration: item['completed'] == true
                                        ? TextDecoration.lineThrough
                                        : null,
                                  ),
                                ),
                                subtitle: Text(item['category']),
                                trailing: item['completed'] == true
                                    ? null
                                    : IconButton(
                                        icon: const Icon(Icons.check_circle_outline, color: Colors.green),
                                        onPressed: () => _completeItem(
                                          order['id'],
                                          item['id'],
                                          item['name'],
                                        ),
                                      ),
                              );
                            }).toList(),
                            const SizedBox(height: 8),
                            Align(
                              alignment: Alignment.centerRight,
                              child: ElevatedButton(
                                style: ElevatedButton.styleFrom(
                                  backgroundColor: allItemsCompleted 
                                      ? Colors.green 
                                      : Colors.orange,
                                ),
                                onPressed: () => _completeOrder(order['id']),
                                child: Text(
                                  allItemsCompleted 
                                      ? 'Complete Order' 
                                      : 'Force Complete',
                                ),
                              ),
                            ),
                          ],
                        ),
                      ),
                    );
                  },
                ),
    );
  }

  @override
  void dispose() {
    socket.disconnect();
    super.dispose();
  }
}
