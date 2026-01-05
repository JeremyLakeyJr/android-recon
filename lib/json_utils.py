#!/usr/bin/env python3
"""
Linux Recon - JSON Output Utilities
====================================
Provides consistent JSON formatting and output functions for all scanner modules.
"""

import json
import os
import sys
from datetime import datetime
from typing import Any, Dict, List, Optional, Union


def get_timestamp() -> str:
    """Get current timestamp in ISO format."""
    return datetime.now().isoformat()


def create_scan_result(
    scan_type: str,
    data: Union[List, Dict],
    metadata: Optional[Dict] = None
) -> Dict[str, Any]:
    """
    Create a standardized scan result structure.
    
    Args:
        scan_type: Type of scan (network, wifi, bluetooth)
        data: Scan results data
        metadata: Optional additional metadata
    
    Returns:
        Standardized scan result dictionary
    """
    result = {
        "scan_type": scan_type,
        "timestamp": get_timestamp(),
        "version": "1.0.0",
        "data": data,
        "metadata": metadata or {}
    }
    
    # Add count if data is a list
    if isinstance(data, list):
        result["count"] = len(data)
    
    return result


def save_json(
    data: Dict[str, Any],
    output_dir: str,
    filename: Optional[str] = None,
    scan_type: Optional[str] = None
) -> str:
    """
    Save scan results to a JSON file.
    
    Args:
        data: Data to save
        output_dir: Directory to save to
        filename: Optional custom filename
        scan_type: Type of scan (used for default filename)
    
    Returns:
        Path to saved file
    """
    # Ensure output directory exists
    os.makedirs(output_dir, exist_ok=True)
    
    # Generate filename if not provided
    if not filename:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        scan_type = scan_type or data.get("scan_type", "scan")
        filename = f"{scan_type}_{timestamp}.json"
    
    filepath = os.path.join(output_dir, filename)
    
    with open(filepath, 'w') as f:
        json.dump(data, f, indent=2, default=str)
    
    return filepath


def load_json(filepath: str) -> Dict[str, Any]:
    """
    Load scan results from a JSON file.
    
    Args:
        filepath: Path to JSON file
    
    Returns:
        Loaded data dictionary
    """
    with open(filepath, 'r') as f:
        return json.load(f)


def print_json(data: Dict[str, Any], pretty: bool = True) -> None:
    """
    Print data as JSON to stdout.
    
    Args:
        data: Data to print
        pretty: Whether to pretty-print with indentation
    """
    if pretty:
        print(json.dumps(data, indent=2, default=str))
    else:
        print(json.dumps(data, default=str))


def get_latest_scan(output_dir: str, scan_type: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """
    Get the most recent scan result from output directory.
    
    Args:
        output_dir: Directory containing scan results
        scan_type: Optional filter by scan type
    
    Returns:
        Latest scan result or None if no scans found
    """
    if not os.path.exists(output_dir):
        return None
    
    # Get all JSON files
    json_files = []
    for f in os.listdir(output_dir):
        if f.endswith('.json'):
            if scan_type is None or f.startswith(scan_type):
                json_files.append(os.path.join(output_dir, f))
    
    if not json_files:
        return None
    
    # Sort by modification time and get the latest
    latest_file = max(json_files, key=os.path.getmtime)
    return load_json(latest_file)


def merge_scans(scans: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Merge multiple scan results into a single combined result.
    
    Args:
        scans: List of scan results to merge
    
    Returns:
        Combined scan result
    """
    combined = {
        "scan_type": "combined",
        "timestamp": get_timestamp(),
        "version": "1.0.0",
        "scans": {},
        "metadata": {
            "source_scans": len(scans)
        }
    }
    
    for scan in scans:
        scan_type = scan.get("scan_type", "unknown")
        combined["scans"][scan_type] = scan
    
    return combined


class ScanResultBuilder:
    """Builder class for creating scan results with consistent structure."""
    
    def __init__(self, scan_type: str):
        """Initialize builder with scan type."""
        self.scan_type = scan_type
        self.items: List[Dict[str, Any]] = []
        self.metadata: Dict[str, Any] = {}
        self.errors: List[str] = []
        self.warnings: List[str] = []
    
    def add_item(self, item: Dict[str, Any]) -> 'ScanResultBuilder':
        """Add an item to the scan results."""
        self.items.append(item)
        return self
    
    def add_metadata(self, key: str, value: Any) -> 'ScanResultBuilder':
        """Add metadata to the scan results."""
        self.metadata[key] = value
        return self
    
    def add_error(self, error: str) -> 'ScanResultBuilder':
        """Add an error message."""
        self.errors.append(error)
        return self
    
    def add_warning(self, warning: str) -> 'ScanResultBuilder':
        """Add a warning message."""
        self.warnings.append(warning)
        return self
    
    def build(self) -> Dict[str, Any]:
        """Build and return the final scan result."""
        result = create_scan_result(
            scan_type=self.scan_type,
            data=self.items,
            metadata=self.metadata
        )
        
        if self.errors:
            result["errors"] = self.errors
        
        if self.warnings:
            result["warnings"] = self.warnings
        
        return result
    
    def save(self, output_dir: str) -> str:
        """Build and save the scan result."""
        return save_json(self.build(), output_dir, scan_type=self.scan_type)


if __name__ == "__main__":
    # Example usage
    builder = ScanResultBuilder("test")
    builder.add_item({"id": 1, "name": "Test Device"})
    builder.add_item({"id": 2, "name": "Test Device 2"})
    builder.add_metadata("scanner_version", "1.0.0")
    
    result = builder.build()
    print_json(result)
