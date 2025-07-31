from typing import List, Optional, Tuple

from simulation.terrain_type import TerrainType
from simulation.world import BASE_ENERGY_COST_PER_MOVE, World, get_energy_cost


class Node:
    """
    A helper class representing a single node in an A* search space.
    """

    def __init__(
        self,
        parent: Optional["Node"] = None,
        position: Optional[Tuple[int, int]] = None,
    ):
        self.parent = parent
        self.position = position

        # The three A* costs
        self.g: float = 0.0  # cost from start node to this node
        self.h: float = 0.0  # heuristic cost from this node to the end

    @property
    def f(self) -> float:
        return self.g + self.h

    def __eq__(self, other: object) -> bool:
        """
        Defines how to check if two nodes are equal
        """
        if not isinstance(other, Node):
            return NotImplemented
        return self.position == other.position


def find_path(
    world: World, start_pos: Tuple[int, int], end_pos: Tuple[int, int]
) -> Optional[List[Tuple[int, int]]]:
    """
    Finds the least energy-cost path from a start to an end position using A*.
    """
    start_node = Node(None, start_pos)
    start_tile = world.get_tile(start_pos[0], start_pos[1])
    if start_tile["terrain"] == TerrainType.WATER:
        raise ValueError(
            f"Pathfinding error: Start position {start_pos} is on unwalkable terrain"
        )

    end_node = Node(None, end_pos)
    end_tile = world.get_tile(end_pos[0], end_pos[1])
    if end_tile["terrain"] == TerrainType.WATER:
        raise ValueError(
            f"Pathfinding error: End position {end_pos} is on unwalkable terrain"
        )

    open_list: List[Node] = [start_node]
    closed_set: set[Tuple[int, int]] = set()

    while len(open_list) > 0:
        current_node = min(open_list, key=lambda node: node.f)
        current_tile = world.get_tile(
            current_node.position[0], current_node.position[1]
        )

        open_list.remove(current_node)
        closed_set.add(current_node.position)

        if current_node == end_node:
            path = []
            current = current_node
            while current is not None:
                path.append(current.position)
                current = current.parent
            # reverse the path before returning
            return path[::-1]

        for new_position in [
            (0, -1),
            (0, 1),
            (-1, 0),
            (1, 0),
            (-1, -1),
            (-1, 1),
            (1, -1),
            (1, 1),
        ]:
            node_position = (
                current_node.position[0] + new_position[0],
                current_node.position[1] + new_position[1],
            )

            # Do not pathfind into water
            neighbor_tile = world.get_tile(node_position[0], node_position[1])
            if neighbor_tile["terrain"] == TerrainType.WATER:
                continue

            child = Node(current_node, node_position)
            if child.position in closed_set:
                continue

            child_tile = world.get_tile(child.position[0], child.position[1])

            # the g_cost is the cost to the parent + the cost of the next step,
            # which is given by moving in the world.
            energy_cost = get_energy_cost(current_tile, child_tile)

            child.g = current_node.g + energy_cost

            # h_cost is an estimate of the remaining cost
            # Option 1: safe and simple
            # child.h = ((child.position[0] - end_node.position[0]) ** 2) + ((child.position[1] - end_node.position[1]) ** 2)

            # Option 2: factor in energy.  possibly inadmissable.
            # Calculate the straight-line distance
            distance = ((child.position[0] - end_node.position[0]) ** 2) + (
                (child.position[1] - end_node.position[1]) ** 2
            )

            # Calculate the energy cost as if we teleported from start to end
            teleport_cost = get_energy_cost(child_tile, end_tile)

            child.h = (distance * BASE_ENERGY_COST_PER_MOVE) + (
                teleport_cost - BASE_ENERGY_COST_PER_MOVE
            )

            existing_node_found = False
            for i, open_node in enumerate(open_list):
                if open_node == child:
                    existing_node_found = True
                    if child.g < open_node.g:
                        open_list[i] = child
                    break

            if not existing_node_found:
                open_list.append(child)

    return None
