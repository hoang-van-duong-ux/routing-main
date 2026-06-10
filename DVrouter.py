#####################################################
# DVrouter.py
# Name:
# HUID:
#####################################################

from router import Router
from packet import Packet
import json

class DVrouter(Router):
    """Distance vector routing protocol implementation."""

    def __init__(self, addr, heartbeat_time):
        Router.__init__(self, addr)  # Initialize base class - DO NOT REMOVE
        self.heartbeat_time = heartbeat_time
        self.last_time = 0

        # --- Đổi tên self.links thành self.link_costs để tránh trùng với class cha ---
        self.link_costs = {}       # port -> cost
        self.neighbors = {}        # port -> neighbor_addr
        
        # Khoảng cách của chính mình: { dest_addr: cost }
        self.distance_vector = { self.addr: 0 } 
        
        # Bảng định tuyến từ hàng xóm: { neighbor_addr: { dest_addr: cost } }
        self.routing_table = {}    
        
        # Bảng chuyển tiếp: { dest_addr: port }
        self.forwarding_table = {} 

    def handle_packet(self, port, packet):
        """Process incoming packet."""
        if packet.is_traceroute:
            # Gói tin dữ liệu thông thường -> Chuyển tiếp dựa trên forwarding table
            if packet.dst_addr in self.forwarding_table:
                next_port = self.forwarding_table[packet.dst_addr]
                self.send(next_port, packet)
        else:
            # Gói tin định tuyến do các router khác gửi đến dưới dạng JSON string
            neighbor_addr = packet.src_addr
            self.neighbors[port] = neighbor_addr
            
            # Đọc dữ liệu vector khoảng cách nhận được từ hàng xóm
            received_dv = json.loads(packet.content)
            
            # Cập nhật thông tin của hàng xóm vào routing_table
            self.routing_table[neighbor_addr] = received_dv
            
            # Tính toán lại bảng định tuyến
            self.update_routing()

    def handle_new_link(self, port, endpoint, cost):
        """Handle new link."""
        self.link_costs[port] = cost
        self.neighbors[port] = endpoint
        
        # Cập nhật lại định tuyến và phát sóng cho các hàng xóm khác
        self.update_routing()

    def handle_remove_link(self, port):
        """Handle removed link."""
        if port in self.link_costs:
            del self.link_costs[port]
        
        # Xóa hàng xóm tương ứng khỏi danh sách và bảng định tuyến
        if port in self.neighbors:
            neighbor_addr = self.neighbors[port]
            if neighbor_addr in self.routing_table:
                del self.routing_table[neighbor_addr]
            del self.neighbors[port]
            
        # Tính toán lại sau khi mất link
        self.update_routing()

    def handle_time(self, time_ms):
        """Handle current time (Gửi định kỳ heartbeat)."""
        if time_ms - self.last_time >= self.heartbeat_time:
            self.last_time = time_ms
            # Phát sóng định kỳ cho tất cả hàng xóm biết vị trí của mình
            self.broadcast_dv()

    def update_routing(self):
        """Tính toán lại Distance Vector và Forwarding Table theo thuật toán Bellman-Ford."""
        new_dv = { self.addr: 0 }
        new_fw = {}
        
        for port, cost in self.link_costs.items():
            neighbor = self.neighbors.get(port)
            if neighbor is None:
                continue
                
            if neighbor not in new_dv or cost < new_dv[neighbor]:
                new_dv[neighbor] = cost
                new_fw[neighbor] = port
         
            if neighbor in self.routing_table:
                for dest, neighbor_to_dest_cost in self.routing_table[neighbor].items():
                    if dest == self.addr:
                        continue 
                        
                    total_cost = cost + neighbor_to_dest_cost
                    if dest not in new_dv or total_cost < new_dv[dest]:
                        new_dv[dest] = total_cost
                        new_fw[dest] = port

        if new_dv != self.distance_vector:
            self.distance_vector = new_dv
            self.forwarding_table = new_fw
            self.broadcast_dv()

    def broadcast_dv(self):
        """Gửi bản tin định tuyến (Distance Vector) tới tất cả các cổng đang kết nối."""
        packet_content = json.dumps(self.distance_vector)
        
        for port in self.link_costs.keys():
            # Tạo gói tin định tuyến (is_traceroute=False)
            routing_packet = Packet(
                kind=Packet.ROUTING, 
                src_addr=self.addr, 
                dst_addr=None, 
                content=packet_content
            )
            self.send(port, routing_packet)

    def __repr__(self):
        """Representation for debugging in the network visualizer."""
        return f"DVrouter(addr={self.addr}, DV={self.distance_vector})"