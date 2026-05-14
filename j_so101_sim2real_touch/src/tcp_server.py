"""TCP 通信服务器"""
import socket
import json
import threading


class TCPServer:
    def __init__(self, port=8765):
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server_socket.bind(('0.0.0.0', port))
        self.server_socket.listen(1)
        self.client_connected = False
        self.joint_pos_target = None
        print(f"[TCP] 服务器监听端口 {port}")

    def accept_connection(self):
        if not self.client_connected:
            try:
                self.server_socket.settimeout(0.001)
                try:
                    client_socket, client_addr = self.server_socket.accept()
                    thread = threading.Thread(target=self._handle_client, args=(client_socket, client_addr), daemon=True)
                    thread.start()
                    self.client_connected = True
                    print(f"[TCP] 已连接: {client_addr}")
                except socket.timeout:
                    pass
            except:
                pass

    def _handle_client(self, client_socket, client_addr):
        buffer = ""
        try:
            while True:
                data = client_socket.recv(4096)
                if not data:
                    break
                buffer += data.decode('utf-8')
                while "\n" in buffer:
                    line, buffer = buffer.split("\n", 1)
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        msg = json.loads(line)
                        if "joint_pos" in msg:
                            self.joint_pos_target = msg["joint_pos"]
                    except json.JSONDecodeError:
                        pass
        except Exception as e:
            print(f"[TCP] 连接错误: {e}")
        finally:
            client_socket.close()
            print(f"[TCP] 客户端断开: {client_addr}")
            self.client_connected = False
            self.joint_pos_target = None

    def close(self):
        self.server_socket.close()
