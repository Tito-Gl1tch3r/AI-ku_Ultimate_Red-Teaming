import unittest
   from unittest.mock import patch
   from astra.network import extract_ips, is_host_alive, scan_port

   class TestNetwork(unittest.TestCase):
       def test_extract_ips(self):
           cidrs = ["192.168.1.0/30"]
           ips = extract_ips(cidrs, max_ips=2)
           expected = ["192.168.1.0", "192.168.1.1"]
           self.assertEqual(ips, expected)

       @patch("socket.socket")
       def test_is_host_alive(self, mock_socket):
           mock_instance = mock_socket.return_value
           mock_instance.connect_ex.return_value = 0  # Simulate success
           result = is_host_alive("127.0.0.1", timeout=1.0)
           self.assertTrue(result)

       @patch("socket.socket")
       def test_scan_port_open(self, mock_socket):
           mock_instance = mock_socket.return_value
           mock_instance.connect_ex.return_value = 0  # Simulate open port
           ip, port, is_open = scan_port("127.0.0.1", 80, timeout=1.0)
           self.assertTrue(is_open)

       @patch("socket.socket")
       def test_scan_port_closed(self, mock_socket):
           mock_instance = mock_socket.return_value
           mock_instance.connect_ex.return_value = 111  # Simulate closed port
           ip, port, is_open = scan_port("127.0.0.1", 80, timeout=1.0)
           self.assertFalse(is_open)

   if __name__ == "__main__":
       unittest.main()