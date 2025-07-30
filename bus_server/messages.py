"""
Message handling for the OpenKore Bus API
Handles serialization and parsing of bus messages using SSM (Simple Serializable Message) format
"""

import struct
from typing import Any, Dict, Optional, Union


class MessageParser:
    """
    Parses incoming messages from the bus protocol using SSM format.
    Based on the OpenKore Bus::MessageParser functionality.
    """
    
    def __init__(self):
        self.buffer = b""
    
    def add(self, data: bytes) -> None:
        """Add data to the parser buffer."""
        self.buffer += data
    
    def read_next(self) -> Optional[tuple[str, Dict[str, Any]]]:
        """
        Read the next complete message from the buffer using SSM format.
        Returns tuple of (message_id, args) or None if no complete message.
        """
        if len(self.buffer) < 4:
            return None
        
        try:
            # Read message length (first 4 bytes, big endian)
            msg_len = struct.unpack('>I', self.buffer[:4])[0]
            
            if len(self.buffer) < msg_len:
                return None
            
            # Extract complete message
            message_data = self.buffer[:msg_len]
            self.buffer = self.buffer[msg_len:]
            
            # Parse SSM message
            message_id, args = _unserialize_ssm(message_data)
            return message_id, args
            
        except Exception as e:
            # Invalid message, clear buffer
            print(f"❌ [PARSER] Invalid SSM message: {e}")
            self.buffer = b""
            return None


def _to_int24(value: int) -> bytes:
    """Convert integer to 24-bit big-endian bytes."""
    return struct.pack('>I', value)[1:4]  # Take last 3 bytes


def _from_int24(data: bytes) -> int:
    """Convert 24-bit big-endian bytes to integer."""
    return struct.unpack('>I', b'\x00' + data)[0]


def _serialize_value(value: Any) -> tuple[int, bytes]:
    """
    Serialize a value and return (type, data).
    Types: 0 = binary, 1 = UTF-8 string, 2 = unsigned integer
    """
    if value is None:
        return 0, b''
    elif isinstance(value, int):
        return 2, struct.pack('>I', value)
    elif isinstance(value, str):
        return 1, value.encode('utf-8')
    elif isinstance(value, bytes):
        return 0, value
    else:
        # Convert to string as fallback
        return 1, str(value).encode('utf-8')


def _unserialize_value(value_type: int, data: bytes) -> Any:
    """Unserialize value data based on type."""
    if value_type == 0:  # Binary
        return data
    elif value_type == 1:  # UTF-8 string
        return data.decode('utf-8')
    elif value_type == 2:  # Unsigned integer
        if len(data) == 4:
            return struct.unpack('>I', data)[0]
        else:
            raise ValueError(f"Integer value with invalid length ({len(data)})")
    else:
        raise ValueError(f"Unknown value type: {value_type}")


def _serialize_ssm(message_id: str, args: Optional[Dict[str, Any]] = None) -> bytes:
    """
    Serialize a message using SSM (Simple Serializable Message) format.
    """
    if args is None:
        args = {}
    
    # Header
    options = 0  # Key-value map
    mid_bytes = message_id.encode('utf-8')
    
    header = struct.pack('>I B B', 0, options, len(mid_bytes)) + mid_bytes
    
    # Serialize key-value pairs
    body = b''
    for key, value in args.items():
        key_bytes = key.encode('utf-8')
        value_type, value_data = _serialize_value(value)
        
        # Key entry: key_length + key + value_type + value_length + value
        body += struct.pack('B', len(key_bytes))
        body += key_bytes
        body += struct.pack('B', value_type)
        body += _to_int24(len(value_data))
        body += value_data
    
    # Complete message with total length
    total_data = header + body
    total_length = len(total_data)
    
    # Update length in header
    return struct.pack('>I', total_length) + total_data[4:]


def _unserialize_ssm(data: bytes) -> tuple[str, Dict[str, Any]]:
    """
    Unserialize SSM format message.
    Returns (message_id, args).
    """
    if len(data) < 4:
        raise ValueError("Invalid message: too short")
    
    # Read header
    msg_len = struct.unpack('>I', data[:4])[0]
    if len(data) != msg_len:
        raise ValueError("Invalid message: length mismatch")
    
    # Parse header
    offset = 4
    options = struct.unpack('B', data[offset:offset+1])[0]
    offset += 1
    
    mid_len = struct.unpack('B', data[offset:offset+1])[0]
    offset += 1
    
    message_id = data[offset:offset+mid_len].decode('utf-8')
    offset += mid_len
    
    # Parse arguments based on options
    args = {}
    if options == 0:  # Key-value map
        while offset < msg_len:
            # Read key
            key_len = struct.unpack('B', data[offset:offset+1])[0]
            offset += 1
            
            key = data[offset:offset+key_len].decode('utf-8')
            offset += key_len
            
            # Read value type and length
            value_type = struct.unpack('B', data[offset:offset+1])[0]
            offset += 1
            
            value_len = _from_int24(data[offset:offset+3])
            offset += 3
            
            # Read value
            value_data = data[offset:offset+value_len]
            offset += value_len
            
            # Unserialize value
            args[key] = _unserialize_value(value_type, value_data)
    
    return message_id, args


def serialize(message_id: str, args: Optional[Dict[str, Any]] = None) -> bytes:
    """
    Serialize a message for transmission over the bus using SSM format.
    Compatible with OpenKore bus message format.
    """
    if args is None:
        args = {}
    
    full_data = _serialize_ssm(message_id, args)
    return full_data


def deserialize(data: bytes) -> tuple[str, Dict[str, Any]]:
    """
    Deserialize a complete SSM message from bytes.
    Returns tuple of (message_id, args).
    """
    return _unserialize_ssm(data)
