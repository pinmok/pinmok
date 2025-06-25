#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Universal tree structure base class

Description:
  A generic tree utility module providing a base tree node class and functions to build
  and manipulate tree structures from flat node lists.
Author:
  惠达浪 <crazys@126.com>
Created:
  2025-06-09
"""
from dataclasses import field, dataclass
from typing import TypeVar, Generic, Callable, Type, Any, Mapping

# Generic type for TreeNode subclasses
T = TypeVar("T", bound="TreeNode[Any]")


@dataclass(kw_only=True)
class TreeNode(Generic[T]):
    """
    Base class for tree nodes with generic type support.

    Attributes:
        id: Unique identifier of the node (str or int).
        parent_id: Identifier of the parent node (None for root nodes).
        children: List of child nodes (hidden from default repr).
    """

    id: int | str
    parent_id: int | str | None = None
    children: list[T] = field(default_factory=list, repr=False)

    def __post_init__(self):
        """Validate node construction."""
        if self.parent_id == self.id:
            raise ValueError("Node cannot be its own parent")

    def add_child(self, child: T) -> None:
        """Add a single child node to this node."""
        if child.parent_id != self.id:
            raise ValueError(
                f"Child node {child.id} parent_id mismatch: expected {self.id}, got {child.parent_id}"
            )
        self.children.append(child)

    def add_children(self, *children: T) -> None:
        """Add multiple child nodes to this node."""
        for child in children:
            self.add_child(child)

    def remove_child(self, child_id: int | str) -> bool:
        """
        Remove a child node by ID.

        Returns:
            bool: True if child was found and removed, False otherwise.
        """
        initial_count = len(self.children)
        self.children = [c for c in self.children if c.id != child_id]
        return len(self.children) != initial_count

    def find(self, node_id: int | str) -> T | None:
        """
        Find a node by ID in this subtree (depth-first search).

        Returns:
            T|None: The found node or None if not found.
        """
        if self.id == node_id:
            return self
        for child in self.children:
            if found := child.find(node_id):
                return found
        return None

    def traverse(self, func: Callable[[T], None]) -> None:
        """
        Traverse tree in pre-order, applying func to each node.

        Args:
            func: Callable that processes each node.
        """
        func(self)
        for child in self.children:
            child.traverse(func)

    @classmethod
    def build_tree(cls: Type[T], nodes: list[T], sort_key: str | None = None) -> list[T]:
        """
        Build a tree structure from a flat list of nodes.

        Args:
            nodes(list[T]): List of TreeNode instances.
            sort_key(str | None): Optional attribute name to sort children and roots by.

        Returns:
            list[T]: Root nodes of the constructed tree.

        Raises:
            ValueError: If duplicate IDs or invalid parent references to exist.
        """
        node_map: dict[int | str, T] = {node.id: node for node in nodes}
        if len(node_map) != len(nodes):
            raise ValueError("Duplicate node IDs detected")

        roots: list[T] = []
        for node in nodes:
            if node.parent_id:
                if node.parent_id not in node_map:
                    raise ValueError(f"Parent {node.parent_id} not found")
                if node.parent_id == node.id:
                    raise ValueError(f"Node {node.id} cannot be its own parent")
                node_map[node.parent_id].children.append(node)
            else:
                roots.append(node)

        if sort_key:
            def sort_nodes(nodes_list: list[T]):
                nodes_list.sort(key=lambda n: getattr(n, sort_key))

            # Recursive sorting of children for each node
            def sort_tree(nodes_list: list[T]):
                for n in nodes_list:
                    if n.children:
                        sort_tree(n.children)
                        sort_nodes(n.children)

            sort_tree(roots)
            sort_nodes(roots)
            
        return roots

    def find_in_subtree(self, predicate: Callable[[T], bool]) -> T | None:
        """
        Search for a node matching the predicate in this subtree.

        Args:
            predicate: Function that returns True for matching nodes.

        Returns:
            T|None: First matching node or None.
        """
        if predicate(self):
            return self
        for child in self.children:
            if result := child.find_in_subtree(predicate):
                return result
        return None

    def detach_subtree(self, node_id: int | str) -> T | None:
        """
        Detach and return a subtree from this tree.

        Args:
            node_id: ID of the subtree root node.

        Returns:
            T|None: The detached subtree or None if not found.
        """
        node = self.find(node_id)
        if node and node.parent_id:
            if parent := self.find(node.parent_id):
                parent.remove_child(node_id)
                return node
        return None

    def to_dict(
            self,
            include: list[str] | None = None,
            exclude: list[str] | None = None,
            depth: int | None = None
    ) -> dict[str, Any]:
        """
        Convert the node and its children to a dictionary.

        Args:
            include (list[str]|None): A list of attribute names to include.
            exclude (list[str]|None): A list of attribute names to exclude.
            depth (int|None): Maximum recursion depth for converting child nodes.

        Returns:
            dict[str, Any]: A dictionary representation of the node.

        Raises:
            ValueError: If both 'include' and 'exclude' are provided.
        """
        if include and exclude:
            raise ValueError("Cannot specify both 'include' and 'exclude'.")

        field_names = self.__annotations__.keys()

        # Filter fields based on include/exclude
        if include:
            field_names = [f for f in field_names if f in include]
        elif exclude:
            field_names = [f for f in field_names if f not in exclude]

        data = {field: getattr(self, field) for field in field_names}

        # Recursively convert children if within depth limit
        if depth is None or depth > 0:
            child_depth = None if depth is None else depth - 1
            data["children"] = [child.to_dict(include=include, exclude=exclude, depth=child_depth)
                                for child in self.children]
        else:
            data["children"] = []

        return data

    def validate_tree(self) -> None:
        """
        Validate tree structure (check for cycles and parent-child consistency).

        Raises:
            ValueError: If structural problems are found.
        """
        visited_ids = set()

        def _validate(node: TreeNode[T]) -> None:
            if node.id in visited_ids:
                raise ValueError(f"Cycle detected at node {node.id}")
            visited_ids.add(node.id)

            for child in node.children:
                if child.parent_id != node.id:
                    raise ValueError(f"Parent-child mismatch at {child.id}")
                _validate(child)

        _validate(self)

    def attach_subtree(self, parent_id: int | str, subtree: T) -> bool:
        """
        Attach a subtree to a new parent node.

        Args:
            parent_id: ID of the target parent node.
            subtree: The subtree to attach.

        Returns:
            bool: True if attached successfully, False if parent not found.
        """
        if not isinstance(subtree, TreeNode):
            raise ValueError("Subtree must be a valid TreeNode instance")

        parent = self.find(parent_id)
        if not parent:
            return False

        # Check for circular reference
        if subtree.find(parent.id):
            raise ValueError("Circular reference detected")

        subtree.parent_id = parent_id
        parent.children.append(subtree)
        return True

    def to_list(self) -> list[T]:
        """
        Flatten the tree into a list of nodes (pre-order).

        Returns:
            list[T]: List of all nodes in the subtree, starting from this node.
        """
        result: list[T] = []

        if not hasattr(self, 'traverse'):
            return result

        def collect(node: T) -> None:
            if node:
                result.append(node)

        self.traverse(collect)
        return result

    @classmethod
    def build_node(cls: Type[T], data: Any) -> T:
        """
        Create an instance from dict-like data.

        Args:
            data (Mapping): The input data.

        Returns:
            T: The created instance.
        """
        if not isinstance(data, Mapping) and not hasattr(data, "__dict__"):
            raise TypeError(
                f"Unsupported data type: {type(data).__name__}, must be dict-like or object."
            )

        if not isinstance(data, Mapping):
            data = data.__dict__

        field_names = cls.__dataclass_fields__.keys()

        # Only include keys that exist in data, skip missing ones
        kwargs = {key: data.get(key) for key in field_names if key in data}

        return cls(**kwargs)
