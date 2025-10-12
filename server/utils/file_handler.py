# utils/file_handler.py

"""
File handling utilities
"""

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, Any


def save_search_results(data: Dict[str, Any], filename: str = None) -> str:
    """Save search results to JSON file"""
    results_dir = "results"
    Path(results_dir).mkdir(exist_ok=True)

    if filename is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        query_safe = "".join(
            c for c in data.get('query', 'search')
            if c.isalnum() or c in (' ', '-', '_')
        )[:30]
        filename = f"search_{query_safe}_{timestamp}.json"

    filepath = os.path.join(results_dir, filename)

    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    return filepath


def save_error_log(error_data: Dict[str, Any]) -> str:
    """Save error information to file"""
    errors_dir = "results/errors"
    Path(errors_dir).mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"error_{timestamp}.json"
    filepath = os.path.join(errors_dir, filename)

    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(error_data, f, indent=2, ensure_ascii=False)

    return filepath