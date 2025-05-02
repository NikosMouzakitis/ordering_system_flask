import javax.swing.*;
import java.awt.*;
import java.awt.event.ActionEvent;
import java.awt.event.ActionListener;
import java.io.BufferedReader;
import java.io.IOException;
import java.io.InputStreamReader;
import java.io.OutputStream;
import java.net.HttpURLConnection;
import java.net.URL;
import java.util.ArrayList;
import java.util.List;
import java.util.prefs.Preferences;
import org.json.JSONArray;
import org.json.JSONObject;
import java.net.URI;
import javax.websocket.*;

@ClientEndpoint
public class KitchenDisplaySystem {
    private static final String PREFS_KEY = "server_ip";
    private static String serverIp = "";
    private static List<JSONObject> orders = new ArrayList<>();
    private static boolean isLoading = true;
    private static Session websocketSession;
    
    private static JFrame frame;
    private static JPanel mainPanel;
    private static JButton refreshButton;
    
    public static void main(String[] args) {
        // Load saved server IP
        Preferences prefs = Preferences.userRoot().node(KitchenDisplaySystem.class.getName());
        serverIp = prefs.get(PREFS_KEY, "");
        
        SwingUtilities.invokeLater(() -> {
            createAndShowGUI();
            if (!serverIp.isEmpty()) {
                connectToWebSocket();
                fetchOrders();
            } else {
                showIpConfigDialog();
            }
        });
    }
    
    private static void createAndShowGUI() {
        frame = new JFrame("Kitchen Display System");
        frame.setDefaultCloseOperation(JFrame.EXIT_ON_CLOSE);
        frame.setExtendedState(JFrame.MAXIMIZED_BOTH); // Fullscreen mode
        
        mainPanel = new JPanel(new BorderLayout());
        
        // Create toolbar
        JToolBar toolBar = new JToolBar();
        refreshButton = new JButton("Refresh");
        refreshButton.addActionListener(e -> fetchOrders());
        toolBar.add(refreshButton);
        
        frame.add(toolBar, BorderLayout.NORTH);
        frame.add(mainPanel, BorderLayout.CENTER);
        
        frame.setVisible(true);
    }
    
    private static void showIpConfigDialog() {
        JPanel panel = new JPanel(new BorderLayout(5, 5));
        panel.add(new JLabel("Server IP Address:"), BorderLayout.WEST);
        JTextField ipField = new JTextField(serverIp, 15);
        panel.add(ipField, BorderLayout.CENTER);
        
        int result = JOptionPane.showConfirmDialog(
            frame, 
            panel, 
            "Server Configuration", 
            JOptionPane.OK_CANCEL_OPTION, 
            JOptionPane.PLAIN_MESSAGE
        );
        
        if (result == JOptionPane.OK_OPTION) {
            serverIp = ipField.getText().trim();
            if (!serverIp.isEmpty()) {
                Preferences prefs = Preferences.userRoot().node(KitchenDisplaySystem.class.getName());
                prefs.put(PREFS_KEY, serverIp);
                connectToWebSocket();
                fetchOrders();
            }
        }
    }
    
    private static void connectToWebSocket() {
        try {
            WebSocketContainer container = ContainerProvider.getWebSocketContainer();
            container.connectToServer(new Endpoint() {
                @Override
                public void onOpen(Session session, EndpointConfig config) {
                    System.out.println("Connected to KDS server");
                    websocketSession = session;
                    
                    session.addMessageHandler(new MessageHandler.Whole<String>() {
                        @Override
                        public void onMessage(String message) {
                            System.out.println("WebSocket message received: " + message);
                            SwingUtilities.invokeLater(() -> {
                                // Immediately refresh orders when we get any message
                                fetchOrders();
                            });
                        }
                    });
                }
            }, URI.create("ws://" + serverIp + ":5000"));
        } catch (Exception e) {
            System.err.println("WebSocket connection error: " + e.getMessage());
            JOptionPane.showMessageDialog(frame, "WebSocket connection error: " + e.getMessage(), 
                "Connection Error", JOptionPane.ERROR_MESSAGE);
        }
    }
    
    private static void fetchOrders() {
        SwingUtilities.invokeLater(() -> {
            mainPanel.removeAll();
            mainPanel.add(new JLabel("Loading orders...", SwingConstants.CENTER), BorderLayout.CENTER);
            mainPanel.revalidate();
            mainPanel.repaint();
        });
        
        new Thread(() -> {
            try {
                URL url = new URL("http://" + serverIp + ":5000/api/kds/orders?station=kitchen");
                HttpURLConnection conn = (HttpURLConnection) url.openConnection();
                conn.setRequestMethod("GET");
                
                int responseCode = conn.getResponseCode();
                if (responseCode == HttpURLConnection.HTTP_OK) {
                    BufferedReader in = new BufferedReader(new InputStreamReader(conn.getInputStream()));
                    String inputLine;
                    StringBuilder response = new StringBuilder();
                    
                    while ((inputLine = in.readLine()) != null) {
                        response.append(inputLine);
                    }
                    in.close();
                    
                    JSONArray ordersArray = new JSONArray(response.toString());
                    orders.clear();
                    for (int i = 0; i < ordersArray.length(); i++) {
                        orders.add(ordersArray.getJSONObject(i));
                    }
                    
                    SwingUtilities.invokeLater(() -> updateOrdersDisplay());
                } else {
                    throw new IOException("HTTP error code: " + responseCode);
                }
            } catch (Exception e) {
                System.err.println("Error fetching orders: " + e.getMessage());
                SwingUtilities.invokeLater(() -> {
                    JOptionPane.showMessageDialog(frame, "Error loading orders: " + e.getMessage(), 
                        "Error", JOptionPane.ERROR_MESSAGE);
                    mainPanel.removeAll();
                    mainPanel.add(new JLabel("Error loading orders", SwingConstants.CENTER), BorderLayout.CENTER);
                    mainPanel.revalidate();
                    mainPanel.repaint();
                });
            }
        }).start();
    }
    
    private static void updateOrdersDisplay() {
        mainPanel.removeAll();
        mainPanel.setLayout(new BorderLayout());

        if (orders.isEmpty()) {
            mainPanel.add(new JLabel("No pending orders", SwingConstants.CENTER), BorderLayout.CENTER);
            mainPanel.revalidate();
            mainPanel.repaint();
            return;
        }

        // Create a scrollable container for our grid
        JPanel gridContainer = new JPanel();
        gridContainer.setLayout(new BoxLayout(gridContainer, BoxLayout.Y_AXIS));
        
        // Calculate how many rows we need (2 orders per row)
        int rows = (int) Math.ceil(orders.size() / 2.0);
        
        for (int row = 0; row < rows; row++) {
            JPanel rowPanel = new JPanel();
            rowPanel.setLayout(new GridLayout(1, 2, 10, 10));
            rowPanel.setMaximumSize(new Dimension(Integer.MAX_VALUE, 400));
            
            // Add 2 orders per row
            for (int col = 0; col < 2; col++) {
                int index = row * 2 + col;
                if (index < orders.size()) {
                    rowPanel.add(createOrderPanel(orders.get(index)));
                } else {
                    // Add empty panel to maintain grid structure
                    rowPanel.add(new JPanel());
                }
            }
            
            gridContainer.add(rowPanel);
            gridContainer.add(Box.createRigidArea(new Dimension(0, 10)));
        }

        JScrollPane scrollPane = new JScrollPane(gridContainer);
        scrollPane.setBorder(BorderFactory.createEmptyBorder());
        mainPanel.add(scrollPane, BorderLayout.CENTER);
        mainPanel.revalidate();
        mainPanel.repaint();
    }
    
    private static JPanel createOrderPanel(JSONObject order) {
        JPanel orderPanel = new JPanel(new BorderLayout());
        orderPanel.setBorder(BorderFactory.createCompoundBorder(
            BorderFactory.createLineBorder(Color.ORANGE, 2),
            BorderFactory.createEmptyBorder(10, 10, 10, 10)
        ));
        
        // Header with table and wait time
        JPanel headerPanel = new JPanel(new BorderLayout());
        JLabel tableLabel = new JLabel("Table " + order.getInt("table_id"));
        tableLabel.setFont(tableLabel.getFont().deriveFont(Font.BOLD, 16));
        headerPanel.add(tableLabel, BorderLayout.WEST);
        
        JLabel waitTimeLabel = new JLabel("Waiting: " + order.getString("wait_time"));
        waitTimeLabel.setFont(waitTimeLabel.getFont().deriveFont(Font.PLAIN, 14));
        waitTimeLabel.setForeground(Color.GRAY);
        headerPanel.add(waitTimeLabel, BorderLayout.EAST);
        
        orderPanel.add(headerPanel, BorderLayout.NORTH);
        
        // Items list with scroll
        JPanel itemsPanel = new JPanel();
        itemsPanel.setLayout(new BoxLayout(itemsPanel, BoxLayout.Y_AXIS));
        
        JSONArray items = order.getJSONArray("items");
        boolean allItemsCompleted = true;
        
        for (int i = 0; i < items.length(); i++) {
            JSONObject item = items.getJSONObject(i);
            if (!item.getBoolean("completed")) {
                allItemsCompleted = false;
            }
            
            JPanel itemPanel = new JPanel(new BorderLayout());
            itemPanel.setBorder(BorderFactory.createEmptyBorder(5, 0, 5, 0));
            
            // Item status indicator
            JLabel statusLabel = new JLabel();
            statusLabel.setPreferredSize(new Dimension(20, 20));
            if (item.getBoolean("completed")) {
                statusLabel.setIcon(new ImageIcon("check.png")); // You should provide this image
            }
            itemPanel.add(statusLabel, BorderLayout.WEST);
            
            // Item name
            JLabel nameLabel = new JLabel(item.getString("name"));
            nameLabel.setFont(nameLabel.getFont().deriveFont(Font.PLAIN, 14));
            if (item.getBoolean("completed")) {
                nameLabel.setForeground(Color.GRAY);
            }
            itemPanel.add(nameLabel, BorderLayout.CENTER);
            
            // Complete button if not completed
            if (!item.getBoolean("completed")) {
                JButton completeButton = new JButton("✓");
                completeButton.setFont(completeButton.getFont().deriveFont(Font.BOLD, 14));
                completeButton.setBackground(Color.GREEN);
                completeButton.addActionListener(new CompleteItemListener(order.getInt("id"), item.getInt("id")));
                itemPanel.add(completeButton, BorderLayout.EAST);
            }
            
            itemsPanel.add(itemPanel);
        }
        
        JScrollPane itemsScrollPane = new JScrollPane(itemsPanel);
        itemsScrollPane.setBorder(BorderFactory.createEmptyBorder());
        orderPanel.add(itemsScrollPane, BorderLayout.CENTER);
        
        // Complete order button
        JButton completeOrderButton = new JButton(allItemsCompleted ? "COMPLETE ORDER" : "FORCE COMPLETE");
        completeOrderButton.setFont(completeOrderButton.getFont().deriveFont(Font.BOLD, 14));
        completeOrderButton.setBackground(allItemsCompleted ? Color.GREEN : Color.ORANGE);
        completeOrderButton.addActionListener(new CompleteOrderListener(order.getInt("id")));
        orderPanel.add(completeOrderButton, BorderLayout.SOUTH);
        
        return orderPanel;
    }
    
    private static class CompleteItemListener implements ActionListener {
        private int orderId;
        private int itemId;
        
        public CompleteItemListener(int orderId, int itemId) {
            this.orderId = orderId;
            this.itemId = itemId;
        }
        
        @Override
        public void actionPerformed(ActionEvent e) {
            new Thread(() -> {
                try {
                    URL url = new URL("http://" + serverIp + ":5000/api/kds/complete_item");
                    HttpURLConnection conn = (HttpURLConnection) url.openConnection();
                    conn.setRequestMethod("POST");
                    conn.setRequestProperty("Content-Type", "application/json");
                    conn.setDoOutput(true);
                    
                    JSONObject requestBody = new JSONObject();
                    requestBody.put("order_id", orderId);
                    requestBody.put("item_id", itemId);
                    
                    try (OutputStream os = conn.getOutputStream()) {
                        byte[] input = requestBody.toString().getBytes("utf-8");
                        os.write(input, 0, input.length);
                    }
                    
                    int responseCode = conn.getResponseCode();
                    if (responseCode != HttpURLConnection.HTTP_OK) {
                        throw new IOException("HTTP error code: " + responseCode);
                    }
                    
                    // No need to manually refresh - WebSocket will trigger refresh
                } catch (Exception ex) {
                    System.err.println("Error completing item: " + ex.getMessage());
                    SwingUtilities.invokeLater(() -> {
                        JOptionPane.showMessageDialog(frame, "Error completing item: " + ex.getMessage(), 
                            "Error", JOptionPane.ERROR_MESSAGE);
                    });
                }
            }).start();
        }
    }
    
    private static class CompleteOrderListener implements ActionListener {
        private int orderId;
        
        public CompleteOrderListener(int orderId) {
            this.orderId = orderId;
        }
        
        @Override
        public void actionPerformed(ActionEvent e) {
            // Find the order to check for pending items
            JSONObject order = null;
            for (JSONObject o : orders) {
                if (o.getInt("id") == orderId) {
                    order = o;
                    break;
                }
            }
            
            if (order == null) return;
            
            // Check for pending items
            JSONArray items = order.getJSONArray("items");
            List<JSONObject> pendingItems = new ArrayList<>();
            for (int i = 0; i < items.length(); i++) {
                JSONObject item = items.getJSONObject(i);
                if (!item.getBoolean("completed")) {
                    pendingItems.add(item);
                }
            }
            
            if (!pendingItems.isEmpty()) {
                int confirm = JOptionPane.showConfirmDialog(frame, 
                    "There are " + pendingItems.size() + " items not marked as prepared.\n" +
                    "Complete the entire order anyway?", 
                    "Complete Order?", 
                    JOptionPane.YES_NO_OPTION);
                
                if (confirm != JOptionPane.YES_OPTION) {
                    return;
                }
            }
            
            new Thread(() -> {
                try {
                    URL url = new URL("http://" + serverIp + ":5000/api/kds/complete");
                    HttpURLConnection conn = (HttpURLConnection) url.openConnection();
                    conn.setRequestMethod("POST");
                    conn.setRequestProperty("Content-Type", "application/json");
                    conn.setDoOutput(true);
                    
                    JSONObject requestBody = new JSONObject();
                    requestBody.put("order_id", orderId);
                    
                    try (OutputStream os = conn.getOutputStream()) {
                        byte[] input = requestBody.toString().getBytes("utf-8");
                        os.write(input, 0, input.length);
                    }
                    
                    int responseCode = conn.getResponseCode();
                    if (responseCode != HttpURLConnection.HTTP_OK) {
                        throw new IOException("HTTP error code: " + responseCode);
                    }
                    
                    // No need to manually refresh - WebSocket will trigger refresh
                } catch (Exception ex) {
                    System.err.println("Error completing order: " + ex.getMessage());
                    SwingUtilities.invokeLater(() -> {
                        JOptionPane.showMessageDialog(frame, "Error completing order: " + ex.getMessage(), 
                            "Error", JOptionPane.ERROR_MESSAGE);
                    });
                }
            }).start();
        }
    }
}
