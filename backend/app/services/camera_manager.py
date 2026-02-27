import socket
import struct
import xml.etree.ElementTree as ET
from typing import List, Dict, Optional
import cv2
import os
import re


class ONVIFDiscovery:
    """Discover ONVIF-compliant cameras on the network."""
    
    WS_DISCOVERY = b'<?xml version="1.0" encoding="utf-8"?><Envelope xmlns:dn="http://www.onvif.org/ver10/network/wsdl" xmlns="http://schemas.xmlsoap.org/soap/envelope/"><Header><wsa:MessageID xmlns:wsa="http://schemas.xmlsoap.org/ws/2004/08/addressing">uuid:%s</wsa:MessageID><wsa:To xmlns:wsa="http://schemas.xmlsoap.org/ws/2004/08/addressing">urn:schemas-xmlsoap-org:wsdl:drvs:2005-04-18</wsa:To><wsa:Action xmlns:wsa="http://schemas.xmlsoap.org/ws/2004/08/addressing">http://schemas.xmlsoap.org/ws/2005/04/discovery/Probe</wsa:Action></Header><Body><Probe xmlns="http://schemas.xmlsoap.org/ws/2005/04/discovery"><Types>dn:NetworkVideoTransmitter</Types></Probe></Body></Envelope>'
    
    MULTICAST_ADDRESS = "239.255.255.250"
    PORT = 3702
    
    def discover(self, timeout: int = 5) -> List[Dict]:
        """Broadcast UDP probe and collect responses."""
        devices = []
        uuid_str = "00000000-0000-0000-0000-000000000000"
        
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.setsockopt(socket.SOL_IP, socket.IP_MULTICAST_TTL, 2)
        sock.settimeout(timeout)
        
        try:
            sock.sendto(self.WS_DISCOVERY.replace(b'%s', uuid_str.encode()), 
                       (self.MULTICAST_ADDRESS, self.PORT))
            
            while True:
                try:
                    data, addr = sock.recvfrom(4096)
                    device = self._parse_probe_match(data, addr)
                    if device:
                        devices.append(device)
                except socket.timeout:
                    break
        except Exception as e:
            print(f"ONVIF discovery error: {e}")
        finally:
            sock.close()
        
        return devices
    
    def _parse_probe_match(self, data: bytes, addr) -> Optional[Dict]:
        """Parse SOAP response from camera."""
        try:
            root = ET.fromstring(data)
            # Extract XAddrs (camera addresses)
            xaddrs = root.findall(".//{http://schemas.xmlsoap.org/ws/2005/04/discovery}XAddrs")
            for xaddr in xaddrs:
                if xaddr.text:
                    return {
                        "type": "ONVIF",
                        "address": xaddr.text.split()[0],  # Take first address
                        "port": 80,
                        "name": addr[0]
                    }
        except Exception as e:
            print(f"Parse error: {e}")
        return None


class USBCameraDetector:
    """Detect locally connected USB cameras."""
    
    def detect(self) -> List[Dict]:
        """Enumerate /dev/video* devices."""
        devices = []
        for i in range(10):  # Check up to video10
            device_path = f"/dev/video{i}"
            if os.path.exists(device_path):
                devices.append({
                    "type": "USB",
                    "address": device_path,
                    "name": f"USB Camera {i}"
                })
        return devices


class RTSPHandler:
    """Handle RTSP stream connections."""
    
    def build_url(self, address: str, port: int, username: str, password: str, path: str = "/stream") -> str:
        """Build RTSP URL from components."""
        if username and password:
            return f"rtsp://{username}:{password}@{address}:{port}{path}"
        return f"rtsp://{address}:{port}{path}"
    
    def parse_url(self, url: str) -> Dict:
        """Parse RTSP URL into components."""
        match = re.match(r'rtsp://(?:([^:]+):([^@]+)@)?([^:/]+)(?::(\d+))?(/.*)?', url)
        if match:
            return {
                "username": match.group(1),
                "password": match.group(2),
                "address": match.group(3),
                "port": int(match.group(4) or 554),
                "path": match.group(5) or "/stream"
            }
        return {}
    
    def test_connection(self, url: str, timeout: int = 5) -> bool:
        """Test if RTSP stream is accessible."""
        cap = cv2.VideoCapture(url)
        if cap.isOpened():
            ret, frame = cap.read()
            cap.release()
            return ret
        return False


class CameraManager:
    """Unified camera management."""
    
    def __init__(self):
        self.onvif = ONVIFDiscovery()
        self.usb = USBCameraDetector()
        self.rtsp = RTSPHandler()
    
    def discover_all(self) -> List[Dict]:
        """Discover all available cameras."""
        devices = []
        devices.extend(self.onvif.discover())
        devices.extend(self.usb.detect())
        return devices
    
    def test_camera(self, camera_type: str, address: str, username: str = None, 
                   password: str = None, rtsp_url: str = None) -> bool:
        """Test camera connection."""
        if camera_type == "RTSP" and rtsp_url:
            return self.rtsp.test_connection(rtsp_url_url)
        elif camera_type == "USB":
            return os.path.exists(address)
        elif camera_type == "ONVIF":
            # Simplified ONVIF test - try to open as video device or RTSP
            return self.rtsp.test_connection(f"rtsp://{address}/stream")
        return False
