"""
Response Comparison for Performance Benchmarking

This module provides utilities to compare JSON responses
between two implementations to ensure behavioral equivalence.
"""

import json
from typing import Dict, List, Any, Optional, Union
from decimal import Decimal


class ResponseComparator:
    """Compare JSON responses for behavioral equivalence."""

    def __init__(self, tolerance: float = 0.01):
        """
        Initialize comparator.

        Args:
            tolerance: Tolerance for floating point comparisons
        """
        self.tolerance = tolerance
        self.differences: List[Dict[str, Any]] = []

    def compare(self, response1: Any, response2: Any, path: str = "") -> bool:
        """
        Compare two responses recursively.

        Args:
            response1: First response
            response2: Second response
            path: Current path in the response structure (for error reporting)

        Returns:
            True if responses are equivalent, False otherwise
        """
        self.differences = []
        self._compare_recursive(response1, response2, path)
        return len(self.differences) == 0

    def _compare_recursive(self, obj1: Any, obj2: Any, path: str) -> None:
        """Recursively compare two objects."""
        # Handle None values
        if obj1 is None and obj2 is None:
            return
        if obj1 is None or obj2 is None:
            self.differences.append({
                "path": path,
                "type": "null_mismatch",
                "value1": obj1,
                "value2": obj2,
            })
            return

        # Handle different types
        if type(obj1) != type(obj2):
            self.differences.append({
                "path": path,
                "type": "type_mismatch",
                "type1": type(obj1).__name__,
                "type2": type(obj2).__name__,
                "value1": obj1,
                "value2": obj2,
            })
            return

        # Handle dictionaries
        if isinstance(obj1, dict):
            self._compare_dicts(obj1, obj2, path)
            return

        # Handle lists
        if isinstance(obj1, list):
            self._compare_lists(obj1, obj2, path)
            return

        # Handle numeric values (int, float, Decimal)
        if isinstance(obj1, (int, float, Decimal)):
            self._compare_numbers(obj1, obj2, path)
            return

        # Handle strings
        if isinstance(obj1, str):
            if obj1 != obj2:
                self.differences.append({
                    "path": path,
                    "type": "string_mismatch",
                    "value1": obj1,
                    "value2": obj2,
                })
            return

        # Handle booleans
        if isinstance(obj1, bool):
            if obj1 != obj2:
                self.differences.append({
                    "path": path,
                    "type": "boolean_mismatch",
                    "value1": obj1,
                    "value2": obj2,
                })
            return

        # Handle other types (fallback to equality)
        if obj1 != obj2:
            self.differences.append({
                "path": path,
                "type": "value_mismatch",
                "value1": str(obj1),
                "value2": str(obj2),
            })

    def _compare_dicts(self, dict1: Dict, dict2: Dict, path: str) -> None:
        """Compare two dictionaries."""
        keys1 = set(dict1.keys())
        keys2 = set(dict2.keys())

        # Check for missing keys
        missing_in_2 = keys1 - keys2
        missing_in_1 = keys2 - keys1

        for key in missing_in_2:
            self.differences.append({
                "path": f"{path}.{key}",
                "type": "missing_key_in_response2",
                "key": key,
                "value": dict1[key],
            })

        for key in missing_in_1:
            self.differences.append({
                "path": f"{path}.{key}",
                "type": "missing_key_in_response1",
                "key": key,
                "value": dict2[key],
            })

        # Compare common keys
        common_keys = keys1 & keys2
        for key in common_keys:
            self._compare_recursive(
                dict1[key],
                dict2[key],
                f"{path}.{key}" if path else key
            )

    def _compare_lists(self, list1: List, list2: List, path: str) -> None:
        """Compare two lists."""
        if len(list1) != len(list2):
            self.differences.append({
                "path": path,
                "type": "list_length_mismatch",
                "length1": len(list1),
                "length2": len(list2),
            })
            # Compare up to the shorter length
            min_len = min(len(list1), len(list2))
        else:
            min_len = len(list1)

        for i in range(min_len):
            self._compare_recursive(
                list1[i],
                list2[i],
                f"{path}[{i}]"
            )

    def _compare_numbers(self, num1: Union[int, float, Decimal], num2: Union[int, float, Decimal], path: str) -> None:
        """Compare two numeric values with tolerance."""
        num1 = float(num1)
        num2 = float(num2)

        if abs(num1 - num2) > self.tolerance:
            self.differences.append({
                "path": path,
                "type": "numeric_mismatch",
                "value1": num1,
                "value2": num2,
                "difference": abs(num1 - num2),
            })

    def get_differences(self) -> List[Dict[str, Any]]:
        """Get list of differences found."""
        return self.differences

    def get_summary(self) -> Dict[str, Any]:
        """Get summary of differences."""
        difference_types = defaultdict(int)
        for diff in self.differences:
            difference_types[diff["type"]] += 1

        return {
            "total_differences": len(self.differences),
            "identical": len(self.differences) == 0,
            "difference_types": dict(difference_types),
            "differences": self.differences[:50],  # First 50 differences
        }


class IgnoredFieldsComparator(ResponseComparator):
    """Comparator that ignores specified fields during comparison."""

    def __init__(self, ignored_fields: List[str], tolerance: float = 0.01):
        """
        Initialize comparator with ignored fields.

        Args:
            ignored_fields: List of field paths to ignore (e.g., ["rows[*].created_at"])
            tolerance: Tolerance for floating point comparisons
        """
        super().__init__(tolerance)
        self.ignored_fields = ignored_fields

    def _compare_recursive(self, obj1: Any, obj2: Any, path: str) -> None:
        """Compare recursively, skipping ignored fields."""
        # Check if this path should be ignored
        if self._is_ignored(path):
            return

        super()._compare_recursive(obj1, obj2, path)

    def _is_ignored(self, path: str) -> bool:
        """Check if a path should be ignored."""
        for ignored in self.ignored_fields:
            # Support wildcard patterns
            if "*" in ignored:
                pattern = ignored.replace("*", ".*")
                import re
                if re.match(pattern, path):
                    return True
            elif path == ignored or path.startswith(ignored + "."):
                return True
        return False


class SizeComparator:
    """Compare response sizes."""

    @staticmethod
    def get_size(response: Any) -> Dict[str, int]:
        """Get size metrics for a response."""
        json_str = json.dumps(response, default=str)
        return {
            "json_bytes": len(json_str.encode('utf-8')),
            "json_chars": len(json_str),
            "estimated_compressed_bytes": len(json_str.encode('utf-8')) * 0.3,  # Rough estimate
        }

    @staticmethod
    def compare_sizes(response1: Any, response2: Any) -> Dict[str, Any]:
        """Compare sizes of two responses."""
        size1 = SizeComparator.get_size(response1)
        size2 = SizeComparator.get_size(response2)

        return {
            "response1": size1,
            "response2": size2,
            "difference_bytes": size2["json_bytes"] - size1["json_bytes"],
            "difference_percent": ((size2["json_bytes"] - size1["json_bytes"]) / size1["json_bytes"] * 100) if size1["json_bytes"] > 0 else 0,
        }
