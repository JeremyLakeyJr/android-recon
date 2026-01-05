#!/usr/bin/env python3
"""
Linux Recon - Export Utilities
===============================
Export scan results to various formats (JSON, CSV).
"""

import argparse
import csv
import json
import os
import sys
from datetime import datetime
from typing import Any, Dict, List, Optional


def load_all_scans(output_dir: str) -> List[Dict[str, Any]]:
    """
    Load all scan results from output directory.
    
    Args:
        output_dir: Directory containing scan results
    
    Returns:
        List of scan results
    """
    scans = []
    
    if not os.path.exists(output_dir):
        return scans
    
    for filename in sorted(os.listdir(output_dir)):
        if filename.endswith('.json'):
            filepath = os.path.join(output_dir, filename)
            try:
                with open(filepath, 'r') as f:
                    scans.append(json.load(f))
            except (json.JSONDecodeError, IOError) as e:
                print(f"Warning: Could not load {filename}: {e}", file=sys.stderr)
    
    return scans


def flatten_scan_data(scan: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Flatten scan data for CSV export.
    
    Args:
        scan: Scan result dictionary
    
    Returns:
        List of flattened dictionaries
    """
    scan_type = scan.get("scan_type", "unknown")
    timestamp = scan.get("timestamp", "")
    data = scan.get("data", [])
    
    if not isinstance(data, list):
        data = [data]
    
    flattened = []
    for item in data:
        flat_item = {
            "scan_type": scan_type,
            "scan_timestamp": timestamp
        }
        
        # Flatten nested dictionaries
        for key, value in item.items():
            if isinstance(value, dict):
                for sub_key, sub_value in value.items():
                    flat_item[f"{key}_{sub_key}"] = sub_value
            elif isinstance(value, list):
                flat_item[key] = ", ".join(str(v) for v in value)
            else:
                flat_item[key] = value
        
        flattened.append(flat_item)
    
    return flattened


def export_to_json(scans: List[Dict[str, Any]], output_path: str) -> str:
    """
    Export scans to a combined JSON file.
    
    Args:
        scans: List of scan results
        output_path: Path to output file
    
    Returns:
        Path to exported file
    """
    combined = {
        "export_timestamp": datetime.now().isoformat(),
        "total_scans": len(scans),
        "scans": scans
    }
    
    with open(output_path, 'w') as f:
        json.dump(combined, f, indent=2, default=str)
    
    return output_path


def export_to_csv(scans: List[Dict[str, Any]], output_path: str) -> str:
    """
    Export scans to a CSV file.
    
    Args:
        scans: List of scan results
        output_path: Path to output file
    
    Returns:
        Path to exported file
    """
    # Flatten all scan data
    all_data = []
    for scan in scans:
        all_data.extend(flatten_scan_data(scan))
    
    if not all_data:
        print("No data to export", file=sys.stderr)
        return output_path
    
    # Get all unique keys
    all_keys = set()
    for item in all_data:
        all_keys.update(item.keys())
    
    # Sort keys with scan_type and timestamp first
    priority_keys = ["scan_type", "scan_timestamp"]
    sorted_keys = priority_keys + sorted(k for k in all_keys if k not in priority_keys)
    
    # Write CSV
    with open(output_path, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=sorted_keys, extrasaction='ignore')
        writer.writeheader()
        writer.writerows(all_data)
    
    return output_path


def main():
    """Main entry point for exporter."""
    parser = argparse.ArgumentParser(description="Export Linux Recon scan results")
    parser.add_argument(
        "--format", "-f",
        choices=["json", "csv"],
        default="json",
        help="Export format (default: json)"
    )
    parser.add_argument(
        "--output", "-o",
        required=True,
        help="Output directory containing scan results"
    )
    parser.add_argument(
        "--export-path", "-e",
        help="Path for exported file (default: auto-generated)"
    )
    
    args = parser.parse_args()
    
    # Load all scans
    scans = load_all_scans(args.output)
    
    if not scans:
        print("No scan results found to export", file=sys.stderr)
        sys.exit(1)
    
    # Generate export path if not provided
    if args.export_path:
        export_path = args.export_path
    else:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        export_path = os.path.join(args.output, f"export_{timestamp}.{args.format}")
    
    # Export based on format
    if args.format == "json":
        result_path = export_to_json(scans, export_path)
    else:
        result_path = export_to_csv(scans, export_path)
    
    print(f"Exported {len(scans)} scan(s) to: {result_path}")


if __name__ == "__main__":
    main()
