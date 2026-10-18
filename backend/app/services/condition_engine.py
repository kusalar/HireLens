import logging
from typing import Any, Dict, List, Optional, Tuple, Union
from datetime import datetime

logger = logging.getLogger(__name__)

MISSING = object()
MAX_EVALUATION_DEPTH = 5
MAX_CONDITION_COUNT = 25


class ConditionEvaluationError(Exception):
    pass


class ConditionEngine:
    """
    Deterministic, sandboxed Abstract Syntax Tree (AST) condition evaluator.
    Strictly prohibits arbitrary code execution (no eval, no exec).
    Validates complexity bounds and explicitly handles missing data.
    """

    @classmethod
    def resolve_field_path(cls, context: Dict[str, Any], path: str) -> Any:
        """
        Resolve dot-delimited field path from context dictionary or object.
        Returns MISSING sentinel if any key along the path does not exist.
        """
        if not path:
            return MISSING

        tokens = path.strip().split(".")
        current = context

        for token in tokens:
            if current is None or current is MISSING:
                return MISSING

            if isinstance(current, dict):
                if token in current:
                    current = current[token]
                else:
                    return MISSING
            elif hasattr(current, token):
                current = getattr(current, token)
            else:
                return MISSING

        return current

    @classmethod
    def evaluate_leaf(
        cls,
        leaf: Dict[str, Any],
        context: Dict[str, Any],
    ) -> Tuple[bool, Dict[str, Any]]:
        """
        Evaluate a single condition leaf against context.
        Returns (result: bool, explainability_log: dict).
        """
        field_path = leaf.get("field", "")
        operator = leaf.get("operator", "EQUALS")
        expected_value = leaf.get("value")

        actual_value = cls.resolve_field_path(context, field_path)
        is_missing = actual_value is MISSING

        log_entry = {
            "field": field_path,
            "operator": operator,
            "expected_value": expected_value,
            "actual_value": None if is_missing else str(actual_value),
            "is_missing": is_missing,
            "matched": False,
        }

        # Handle existence checks first
        if operator == "EXISTS":
            matched = not is_missing and actual_value is not None and actual_value != ""
            log_entry["matched"] = matched
            return matched, log_entry

        if operator == "NOT_EXISTS":
            matched = is_missing or actual_value is None or actual_value == ""
            log_entry["matched"] = matched
            return matched, log_entry

        # If data is missing for other operators, condition cannot be satisfied
        if is_missing or actual_value is None:
            if operator in ("NOT_EQUALS", "NOT_IN", "NOT_CONTAINS"):
                log_entry["matched"] = True
                return True, log_entry
            log_entry["matched"] = False
            return False, log_entry

        # Comparison operators
        try:
            if operator == "EQUALS":
                if isinstance(actual_value, str) and isinstance(expected_value, str):
                    matched = actual_value.strip().lower() == expected_value.strip().lower()
                else:
                    matched = actual_value == expected_value

            elif operator == "NOT_EQUALS":
                if isinstance(actual_value, str) and isinstance(expected_value, str):
                    matched = actual_value.strip().lower() != expected_value.strip().lower()
                else:
                    matched = actual_value != expected_value

            elif operator in ("GREATER_THAN", "GREATER_THAN_OR_EQUAL", "LESS_THAN", "LESS_THAN_OR_EQUAL"):
                num_actual = float(actual_value)
                num_expected = float(expected_value)
                if operator == "GREATER_THAN":
                    matched = num_actual > num_expected
                elif operator == "GREATER_THAN_OR_EQUAL":
                    matched = num_actual >= num_expected
                elif operator == "LESS_THAN":
                    matched = num_actual < num_expected
                elif operator == "LESS_THAN_OR_EQUAL":
                    matched = num_actual <= num_expected
                else:
                    matched = False

            elif operator == "CONTAINS":
                if isinstance(actual_value, (list, tuple, set)):
                    if isinstance(expected_value, str):
                        exp_lower = expected_value.strip().lower()
                        matched = any(
                            str(item).strip().lower() == exp_lower
                            for item in actual_value
                        )
                    else:
                        matched = expected_value in actual_value
                elif isinstance(actual_value, str) and isinstance(expected_value, str):
                    matched = expected_value.strip().lower() in actual_value.lower()
                else:
                    matched = False

            elif operator == "NOT_CONTAINS":
                if isinstance(actual_value, (list, tuple, set)):
                    if isinstance(expected_value, str):
                        exp_lower = expected_value.strip().lower()
                        matched = not any(
                            str(item).strip().lower() == exp_lower
                            for item in actual_value
                        )
                    else:
                        matched = expected_value not in actual_value
                elif isinstance(actual_value, str) and isinstance(expected_value, str):
                    matched = expected_value.strip().lower() not in actual_value.lower()
                else:
                    matched = True

            elif operator == "IN":
                if isinstance(expected_value, (list, tuple, set)):
                    if isinstance(actual_value, str):
                        act_lower = actual_value.strip().lower()
                        matched = any(
                            str(item).strip().lower() == act_lower
                            for item in expected_value
                        )
                    else:
                        matched = actual_value in expected_value
                else:
                    matched = False

            elif operator == "NOT_IN":
                if isinstance(expected_value, (list, tuple, set)):
                    if isinstance(actual_value, str):
                        act_lower = actual_value.strip().lower()
                        matched = not any(
                            str(item).strip().lower() == act_lower
                            for item in expected_value
                        )
                    else:
                        matched = actual_value not in expected_value
                else:
                    matched = True

            else:
                matched = False
        except (ValueError, TypeError) as e:
            logger.warning("Condition comparison failed for %s: %s", field_path, e)
            matched = False

        log_entry["matched"] = matched
        return matched, log_entry

    @classmethod
    def evaluate_node(
        cls,
        node: Optional[Dict[str, Any]],
        context: Dict[str, Any],
        depth: int = 0,
        counter: Optional[List[int]] = None,
    ) -> Tuple[bool, Dict[str, Any]]:
        """
        Recursively evaluate a condition node (leaf or group) with bounded complexity.
        """
        if counter is None:
            counter = [0]

        counter[0] += 1
        if counter[0] > MAX_CONDITION_COUNT:
            raise ConditionEvaluationError(
                f"Workflow condition complexity exceeded: maximum {MAX_CONDITION_COUNT} conditions allowed."
            )

        if depth > MAX_EVALUATION_DEPTH:
            raise ConditionEvaluationError(
                f"Workflow condition nesting exceeded: maximum recursion depth {MAX_EVALUATION_DEPTH} allowed."
            )

        # Empty condition passes by default
        if not node:
            return True, {"logical_operator": "EMPTY", "matched": True, "children": []}

        # Check if node is a leaf
        if "field" in node:
            matched, log_entry = cls.evaluate_leaf(node, context)
            return matched, log_entry

        # Otherwise it's a group
        logical_operator = node.get("logical_operator", "AND").upper()
        children = node.get("conditions", [])

        if not children:
            # Empty AND group is True; empty OR group is False
            matched = (logical_operator == "AND")
            return matched, {
                "logical_operator": logical_operator,
                "matched": matched,
                "children": [],
            }

        child_logs = []
        if logical_operator == "AND":
            group_matched = True
            for child in children:
                res, log = cls.evaluate_node(child, context, depth=depth + 1, counter=counter)
                child_logs.append(log)
                if not res:
                    group_matched = False
            return group_matched, {
                "logical_operator": "AND",
                "matched": group_matched,
                "children": child_logs,
            }

        elif logical_operator == "OR":
            group_matched = False
            for child in children:
                res, log = cls.evaluate_node(child, context, depth=depth + 1, counter=counter)
                child_logs.append(log)
                if res:
                    group_matched = True
            return group_matched, {
                "logical_operator": "OR",
                "matched": group_matched,
                "children": child_logs,
            }

        else:
            raise ConditionEvaluationError(f"Unsupported logical operator: {logical_operator}")

    @classmethod
    def evaluate(
        cls,
        condition_tree: Optional[Union[Dict[str, Any], Any]],
        context: Dict[str, Any],
    ) -> Tuple[bool, Dict[str, Any]]:
        """
        Public entry point to evaluate a condition tree against context.
        Returns (is_matched: bool, explanation_tree: dict).
        """
        if condition_tree is None:
            return True, {"matched": True, "details": "No conditions configured"}

        # Convert Pydantic model to dict if needed
        if hasattr(condition_tree, "model_dump"):
            raw_tree = condition_tree.model_dump()
        elif hasattr(condition_tree, "dict"):
            raw_tree = condition_tree.dict()
        elif isinstance(condition_tree, dict):
            raw_tree = condition_tree
        else:
            raw_tree = {}

        return cls.evaluate_node(raw_tree, context)
