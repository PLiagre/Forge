using System;
using System.Collections.Generic;
using UnityEngine;

namespace Victoria.CityMode
{
    /// <summary>Deterministic four-neighbour navigation owned by the simulation.</summary>
    public sealed class DeterministicNavigationGrid
    {
        const float CellSize = 4f;
        const int GridSize = 128;
        const float Origin = -256f;
        readonly bool[] blocked = new bool[GridSize * GridSize];
        readonly float[] costs = new float[GridSize * GridSize];
        readonly int[] parents = new int[GridSize * GridSize];
        readonly int[] visited = new int[GridSize * GridSize];
        readonly int[] closed = new int[GridSize * GridSize];
        int searchId;

        public int Revision { get; private set; }

        public void Rebuild(CitySnapshot state, BuildingCatalog catalog)
        {
            if (state == null)
                throw new ArgumentNullException(nameof(state));
            Array.Clear(blocked, 0, blocked.Length);
            foreach (var building in state.buildings)
            {
                var definition = catalog.Get(building.archetype);
                var depth = definition.footprintDepth;
                if (building.archetype == BuildingArchetype.Residence && building.parcelId != 0)
                {
                    var parcel = state.parcels.Find(item => item.id == building.parcelId);
                    if (parcel != null)
                        depth += parcel.extensionLevel * 2.5f;
                }
                BlockFootprint(building.position.ToVector3(), definition.footprintWidth, depth);
            }
            var lumberCamp = catalog.Get(BuildingArchetype.LumberCamp);
            foreach (var site in state.productionSites)
                BlockFootprint(site.position.ToVector3(), lumberCamp.footprintWidth,
                    lumberCamp.footprintDepth);
            Revision++;
        }

        public List<CityPoint> FindPath(Vector3 start, Vector3 target)
        {
            var startIndex = FindNearestWalkable(ToIndex(start));
            var goalIndex = FindNearestWalkable(ToIndex(target));
            if (startIndex < 0 || goalIndex < 0)
                return null;
            if (startIndex == goalIndex)
                return new List<CityPoint> { CityPoint.From(ToWorld(goalIndex)) };

            searchId++;
            if (searchId == int.MaxValue)
            {
                Array.Clear(visited, 0, visited.Length);
                Array.Clear(closed, 0, closed.Length);
                searchId = 1;
            }
            var open = new SortedSet<OpenNode>(OpenNodeComparer.Instance);
            costs[startIndex] = 0f;
            parents[startIndex] = -1;
            visited[startIndex] = searchId;
            open.Add(new OpenNode(startIndex, Heuristic(startIndex, goalIndex), 0f));
            var directions = new[] { -GridSize, 1, GridSize, -1 };
            while (open.Count > 0)
            {
                var current = open.Min;
                open.Remove(current);
                if (closed[current.index] == searchId)
                    continue;
                closed[current.index] = searchId;
                if (current.index == goalIndex)
                    return Reconstruct(goalIndex);

                var x = current.index % GridSize;
                for (var directionIndex = 0; directionIndex < directions.Length; directionIndex++)
                {
                    if (directionIndex == 1 && x == GridSize - 1 || directionIndex == 3 && x == 0)
                        continue;
                    var next = current.index + directions[directionIndex];
                    if (next < 0 || next >= blocked.Length || blocked[next] || closed[next] == searchId)
                        continue;
                    var nextCost = costs[current.index] + 1f;
                    if (visited[next] == searchId && nextCost >= costs[next])
                        continue;
                    visited[next] = searchId;
                    costs[next] = nextCost;
                    parents[next] = current.index;
                    open.Add(new OpenNode(next, nextCost + Heuristic(next, goalIndex), nextCost));
                }
            }
            return null;
        }

        public bool IsWalkable(Vector3 position) => !blocked[ToIndex(position)];

        void BlockFootprint(Vector3 center, float width, float depth)
        {
            var minX = Mathf.Clamp(Mathf.FloorToInt((center.x - width * 0.5f - Origin) / CellSize), 0, GridSize - 1);
            var maxX = Mathf.Clamp(Mathf.FloorToInt((center.x + width * 0.5f - Origin) / CellSize), 0, GridSize - 1);
            var minZ = Mathf.Clamp(Mathf.FloorToInt((center.z - depth * 0.5f - Origin) / CellSize), 0, GridSize - 1);
            var maxZ = Mathf.Clamp(Mathf.FloorToInt((center.z + depth * 0.5f - Origin) / CellSize), 0, GridSize - 1);
            for (var z = minZ; z <= maxZ; z++)
                for (var x = minX; x <= maxX; x++)
                    blocked[z * GridSize + x] = true;
        }

        int FindNearestWalkable(int origin)
        {
            if (!blocked[origin])
                return origin;
            var originX = origin % GridSize;
            var originZ = origin / GridSize;
            for (var radius = 1; radius <= 12; radius++)
            {
                for (var z = -radius; z <= radius; z++)
                {
                    for (var x = -radius; x <= radius; x++)
                    {
                        if (Mathf.Abs(x) != radius && Mathf.Abs(z) != radius)
                            continue;
                        var candidateX = originX + x;
                        var candidateZ = originZ + z;
                        if (candidateX < 0 || candidateX >= GridSize || candidateZ < 0 || candidateZ >= GridSize)
                            continue;
                        var candidate = candidateZ * GridSize + candidateX;
                        if (!blocked[candidate])
                            return candidate;
                    }
                }
            }
            return -1;
        }

        List<CityPoint> Reconstruct(int goal)
        {
            var reversed = new List<CityPoint>();
            var current = goal;
            while (current >= 0)
            {
                reversed.Add(CityPoint.From(ToWorld(current)));
                current = parents[current];
            }
            reversed.Reverse();
            if (reversed.Count > 1)
                reversed.RemoveAt(0);
            return reversed;
        }

        static int ToIndex(Vector3 position)
        {
            var x = Mathf.Clamp(Mathf.FloorToInt((position.x - Origin) / CellSize), 0, GridSize - 1);
            var z = Mathf.Clamp(Mathf.FloorToInt((position.z - Origin) / CellSize), 0, GridSize - 1);
            return z * GridSize + x;
        }

        static Vector3 ToWorld(int index)
        {
            var x = index % GridSize;
            var z = index / GridSize;
            return new Vector3(Origin + (x + 0.5f) * CellSize, 0f,
                Origin + (z + 0.5f) * CellSize);
        }

        static float Heuristic(int left, int right)
        {
            var leftX = left % GridSize;
            var leftZ = left / GridSize;
            var rightX = right % GridSize;
            var rightZ = right / GridSize;
            return Mathf.Abs(leftX - rightX) + Mathf.Abs(leftZ - rightZ);
        }

        readonly struct OpenNode
        {
            public readonly int index;
            public readonly float score;
            public readonly float cost;

            public OpenNode(int index, float score, float cost)
            {
                this.index = index;
                this.score = score;
                this.cost = cost;
            }
        }

        sealed class OpenNodeComparer : IComparer<OpenNode>
        {
            public static readonly OpenNodeComparer Instance = new OpenNodeComparer();
            public int Compare(OpenNode left, OpenNode right)
            {
                var score = left.score.CompareTo(right.score);
                if (score != 0) return score;
                var cost = left.cost.CompareTo(right.cost);
                if (cost != 0) return cost;
                return left.index.CompareTo(right.index);
            }
        }
    }
}
