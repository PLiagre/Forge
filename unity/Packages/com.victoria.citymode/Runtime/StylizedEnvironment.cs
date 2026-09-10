using System;
using System.Collections.Generic;
using UnityEngine;
using UnityEngine.Rendering;
using UnityEngine.Rendering.Universal;

namespace Victoria.CityMode
{
    /// <summary>
    /// Presentation-only helpers for the host prototype. The simulation never
    /// depends on these objects, so the final game can replace them with authored
    /// prefabs, splines and GPU vegetation without changing city state.
    /// </summary>
    public static class StylizedEnvironment
    {
        public static GameObject CreateTerrainRoad(
            string label,
            Vector3 start,
            Vector3 end,
            float width,
            Terrain terrain,
            Material material)
        {
            var delta = end - start;
            delta.y = 0f;
            var length = delta.magnitude;
            var direction = length > 0.001f ? delta / length : Vector3.forward;
            var side = new Vector3(direction.z, 0f, -direction.x);
            var segmentCount = Mathf.Clamp(Mathf.CeilToInt(length / 2.5f), 2, 96);
            var vertices = new Vector3[(segmentCount + 1) * 2];
            var uvs = new Vector2[vertices.Length];
            var triangles = new int[segmentCount * 6];

            for (var i = 0; i <= segmentCount; i++)
            {
                var t = i / (float)segmentCount;
                var center = Vector3.Lerp(start, end, t);
                var left = center - side * (width * 0.5f);
                var right = center + side * (width * 0.5f);
                left.y = SampleHeight(terrain, left) + 0.055f;
                right.y = SampleHeight(terrain, right) + 0.055f;
                var vertex = i * 2;
                vertices[vertex] = left;
                vertices[vertex + 1] = right;
                var longitudinal = t * length / 5.25f;
                uvs[vertex] = new Vector2(0f, longitudinal);
                uvs[vertex + 1] = new Vector2(1f, longitudinal);

                if (i == segmentCount)
                    continue;
                var triangle = i * 6;
                triangles[triangle] = vertex;
                triangles[triangle + 1] = vertex + 2;
                triangles[triangle + 2] = vertex + 1;
                triangles[triangle + 3] = vertex + 1;
                triangles[triangle + 4] = vertex + 2;
                triangles[triangle + 5] = vertex + 3;
            }

            var mesh = new Mesh { name = label + " terrain mesh" };
            mesh.vertices = vertices;
            mesh.uv = uvs;
            mesh.triangles = triangles;
            mesh.RecalculateNormals();
            mesh.RecalculateTangents();
            mesh.RecalculateBounds();

            var road = new GameObject(label);
            road.AddComponent<MeshFilter>().sharedMesh = mesh;
            road.AddComponent<MeshRenderer>().sharedMaterial = material;
            road.AddComponent<MeshCollider>().sharedMesh = mesh;
            road.isStatic = true;
            return road;
        }

        public static void CreateGroundCover(Terrain terrain, Material baseMaterial)
        {
            var root = new GameObject("Stylized ground cover");
            root.isStatic = true;

            var grass = MakeMaterial(baseMaterial, "Meadow blades", new Color(0.22f, 0.35f, 0.075f));
            grass.SetFloat("_Cull", 0f);
            grass.SetFloat("_Smoothness", 0.02f);
            grass.SetFloat("_ReceiveShadows", 0f);
            grass.EnableKeyword("_RECEIVE_SHADOWS_OFF");
            CreateTuftMesh(root.transform, "Meadow grass tufts", terrain, grass, 140001, 680, 24f, 215f, 0.42f, 0.88f);

            var straw = MakeMaterial(baseMaterial, "Dry grass blades", new Color(0.48f, 0.39f, 0.13f));
            straw.SetFloat("_Cull", 0f);
            straw.SetFloat("_Smoothness", 0.01f);
            straw.SetFloat("_ReceiveShadows", 0f);
            straw.EnableKeyword("_RECEIVE_SHADOWS_OFF");
            CreateTuftMesh(root.transform, "Dry grass tufts", terrain, straw, 140137, 180, 28f, 195f, 0.35f, 0.72f);

            var stone = MakeMaterial(baseMaterial, "Highland field stone", new Color(0.30f, 0.31f, 0.27f));
            stone.SetFloat("_Smoothness", 0.06f);
            CreateRockMesh(root.transform, terrain, stone, 140271, 150);
        }

        public static void CreateVillageDressing(
            Terrain terrain,
            Material baseMaterial,
            Material roadMaterial,
            Material woodMaterial)
        {
            var root = new GameObject("Village atmosphere and dressing");
            var stone = MakeMaterial(baseMaterial, "Well stone", new Color(0.32f, 0.34f, 0.31f));
            var darkWood = MakeMaterial(baseMaterial, "Aged oak", new Color(0.25f, 0.12f, 0.045f));
            var iron = MakeMaterial(baseMaterial, "Forged iron", new Color(0.075f, 0.07f, 0.06f));
            iron.SetFloat("_Metallic", 0.42f);
            iron.SetFloat("_Smoothness", 0.30f);
            var cloth = MakeMaterial(baseMaterial, "Burgundy village cloth", new Color(0.34f, 0.045f, 0.035f));
            cloth.SetFloat("_Smoothness", 0.01f);

            var squareHeight = SampleHeight(terrain, new Vector3(-7f, 0f, 2f));
            var square = Primitive(root.transform, "Trampled village square", PrimitiveType.Cylinder,
                new Vector3(-7f, squareHeight - 0.055f, 2f), new Vector3(13f, 0.055f, 10f), roadMaterial, false);
            square.transform.rotation = Quaternion.Euler(0f, 17f, 0f);

            CreateWell(root.transform, terrain, stone, darkWood, iron);
            CreateMarketProps(root.transform, terrain, darkWood, woodMaterial, cloth);
            CreateFenceRun(root.transform, terrain, darkWood, new Vector3(-15f, 0f, -14.5f), Vector3.right, 9, 2.25f);
            CreateFenceRun(root.transform, terrain, darkWood, new Vector3(7f, 0f, -14.5f), Vector3.right, 6, 2.25f);
            CreateCampfire(root.transform, terrain, baseMaterial, stone, darkWood);
            CreateWindAndMotes(root.transform, baseMaterial);
        }

        public static GameObject CreateLumberCamp(
            string label,
            Vector3 position,
            Terrain terrain,
            Material baseMaterial,
            Material roadMaterial,
            Material woodMaterial)
        {
            position.y = SampleHeight(terrain, position);
            var root = new GameObject(label);
            root.transform.position = position;
            if (position.sqrMagnitude > 0.01f)
                root.transform.rotation = Quaternion.LookRotation(-new Vector3(position.x, 0f, position.z).normalized, Vector3.up);

            var darkWood = MakeMaterial(baseMaterial, "Lumber camp dark timber", new Color(0.22f, 0.10f, 0.035f));
            var canvas = MakeMaterial(baseMaterial, "Lumber camp canvas", new Color(0.34f, 0.19f, 0.08f));
            var iron = MakeMaterial(baseMaterial, "Lumber camp iron", new Color(0.08f, 0.075f, 0.065f));
            iron.SetFloat("_Metallic", 0.52f);
            iron.SetFloat("_Smoothness", 0.28f);

            Primitive(root.transform, "Cleared forest floor", PrimitiveType.Cylinder,
                new Vector3(0f, -0.055f, 0f), new Vector3(5.8f, 0.055f, 4.6f), roadMaterial, false);
            for (var x = -1; x <= 1; x += 2)
            for (var z = -1; z <= 1; z += 2)
                Primitive(root.transform, "Heavy shelter post", PrimitiveType.Cube,
                    new Vector3(x * 2.45f, 1.65f, z * 1.75f), new Vector3(0.26f, 3.3f, 0.26f), darkWood, false);

            var roofLeft = Primitive(root.transform, "Canvas shelter roof", PrimitiveType.Cube,
                new Vector3(-1.32f, 3.35f, 0f), new Vector3(3.25f, 0.16f, 4.15f), canvas, false);
            roofLeft.transform.localRotation = Quaternion.Euler(0f, 0f, -22f);
            var roofRight = Primitive(root.transform, "Canvas shelter roof", PrimitiveType.Cube,
                new Vector3(1.32f, 3.35f, 0f), new Vector3(3.25f, 0.16f, 4.15f), canvas, false);
            roofRight.transform.localRotation = Quaternion.Euler(0f, 0f, 22f);
            Primitive(root.transform, "Shelter ridge beam", PrimitiveType.Cube,
                new Vector3(0f, 3.88f, 0f), new Vector3(0.22f, 0.22f, 4.35f), darkWood, false);

            var timberStack = new GameObject("Timber reserve visual");
            timberStack.transform.SetParent(root.transform, false);
            timberStack.transform.localPosition = new Vector3(3.65f, 0f, 0.55f);
            for (var row = 0; row < 3; row++)
            for (var log = 0; log < 4 - row; log++)
            {
                var cylinder = Primitive(timberStack.transform, "Cut timber", PrimitiveType.Cylinder,
                    new Vector3(0f, 0.26f + row * 0.42f, (log - (3 - row) * 0.5f) * 0.52f),
                    new Vector3(0.22f, 1.45f, 0.22f), woodMaterial, false);
                cylinder.transform.localRotation = Quaternion.Euler(0f, 0f, 90f);
            }

            Primitive(root.transform, "Chopping block", PrimitiveType.Cylinder,
                new Vector3(-3.4f, 0.48f, 1.75f), new Vector3(0.62f, 0.48f, 0.62f), woodMaterial, false);
            var axeHandle = Primitive(root.transform, "Woodcutter axe handle", PrimitiveType.Cylinder,
                new Vector3(-3.25f, 1.25f, 1.72f), new Vector3(0.07f, 0.78f, 0.07f), darkWood, false);
            axeHandle.transform.localRotation = Quaternion.Euler(0f, 0f, -18f);
            var axeHead = Primitive(root.transform, "Woodcutter axe head", PrimitiveType.Cube,
                new Vector3(-2.98f, 1.95f, 1.72f), new Vector3(0.52f, 0.24f, 0.12f), iron, false);
            axeHead.transform.localRotation = Quaternion.Euler(0f, 0f, -18f);

            root.AddComponent<LumberCampVisual>();
            return root;
        }

        public static void ConfigurePostProcessing(Camera camera)
        {
            if (camera == null)
                return;

            var cameraData = camera.GetUniversalAdditionalCameraData();
            cameraData.renderPostProcessing = true;
            cameraData.antialiasing = AntialiasingMode.SubpixelMorphologicalAntiAliasing;
            cameraData.antialiasingQuality = AntialiasingQuality.High;

            var volumeObject = new GameObject("CityLab cinematic grading");
            var volume = volumeObject.AddComponent<Volume>();
            volume.isGlobal = true;
            volume.priority = 10f;
            var profile = ScriptableObject.CreateInstance<VolumeProfile>();
            profile.name = "Runtime CityLab painterly grade";
            volume.sharedProfile = profile;

            var tonemapping = profile.Add<Tonemapping>(true);
            tonemapping.mode.Override(TonemappingMode.ACES);

            var color = profile.Add<ColorAdjustments>(true);
            color.postExposure.Override(0.82f);
            color.contrast.Override(6f);
            color.saturation.Override(3f);
            color.colorFilter.Override(new Color(1f, 0.995f, 0.98f));

            var whiteBalance = profile.Add<WhiteBalance>(true);
            whiteBalance.temperature.Override(2f);
            whiteBalance.tint.Override(-1f);

            var bloom = profile.Add<Bloom>(true);
            bloom.intensity.Override(0.16f);
            bloom.threshold.Override(1.05f);
            bloom.scatter.Override(0.62f);
            bloom.clamp.Override(12f);

            var vignette = profile.Add<Vignette>(true);
            vignette.color.Override(new Color(0.055f, 0.035f, 0.025f));
            vignette.intensity.Override(0.10f);
            vignette.smoothness.Override(0.72f);
        }

        static void CreateTuftMesh(
            Transform parent,
            string label,
            Terrain terrain,
            Material material,
            int seed,
            int count,
            float innerRadius,
            float outerRadius,
            float minHeight,
            float maxHeight)
        {
            var random = new System.Random(seed);
            var vertices = new List<Vector3>(count * 8);
            var uvs = new List<Vector2>(count * 8);
            var triangles = new List<int>(count * 12);

            for (var i = 0; i < count; i++)
            {
                var radius = Mathf.Sqrt(Mathf.Lerp(innerRadius * innerRadius, outerRadius * outerRadius, (float)random.NextDouble()));
                var angle = (float)random.NextDouble() * Mathf.PI * 2f;
                var center = new Vector3(Mathf.Cos(angle) * radius, 0f, Mathf.Sin(angle) * radius);
                center.y = SampleHeight(terrain, center);
                var height = Mathf.Lerp(minHeight, maxHeight, (float)random.NextDouble());
                var width = height * Mathf.Lerp(0.14f, 0.24f, (float)random.NextDouble());
                var yaw = (float)random.NextDouble() * Mathf.PI;
                AddCrossedQuad(vertices, uvs, triangles, center, width, height, yaw);
            }

            var mesh = new Mesh { name = label + " combined mesh", indexFormat = IndexFormat.UInt32 };
            mesh.SetVertices(vertices);
            mesh.SetUVs(0, uvs);
            mesh.SetTriangles(triangles, 0);
            mesh.RecalculateNormals();
            mesh.RecalculateBounds();
            var gameObject = new GameObject(label);
            gameObject.transform.SetParent(parent, false);
            gameObject.AddComponent<MeshFilter>().sharedMesh = mesh;
            gameObject.AddComponent<MeshRenderer>().sharedMaterial = material;
            gameObject.isStatic = true;
        }

        static void AddCrossedQuad(
            List<Vector3> vertices,
            List<Vector2> uvs,
            List<int> triangles,
            Vector3 center,
            float halfWidth,
            float height,
            float yaw)
        {
            for (var plane = 0; plane < 2; plane++)
            {
                var direction = new Vector3(Mathf.Cos(yaw + plane * Mathf.PI * 0.5f), 0f,
                    Mathf.Sin(yaw + plane * Mathf.PI * 0.5f));
                var offset = direction * halfWidth;
                var start = vertices.Count;
                vertices.Add(center - offset);
                vertices.Add(center + offset);
                vertices.Add(center + offset + Vector3.up * height);
                vertices.Add(center - offset + Vector3.up * height * 0.92f);
                uvs.Add(new Vector2(0f, 0f));
                uvs.Add(new Vector2(1f, 0f));
                uvs.Add(new Vector2(1f, 1f));
                uvs.Add(new Vector2(0f, 1f));
                triangles.Add(start);
                triangles.Add(start + 2);
                triangles.Add(start + 1);
                triangles.Add(start);
                triangles.Add(start + 3);
                triangles.Add(start + 2);
            }
        }

        static void CreateRockMesh(Transform parent, Terrain terrain, Material material, int seed, int count)
        {
            var random = new System.Random(seed);
            var vertices = new List<Vector3>(count * 6);
            var triangles = new List<int>(count * 24);
            for (var i = 0; i < count; i++)
            {
                var radius = Mathf.Lerp(38f, 220f, (float)random.NextDouble());
                var angle = (float)random.NextDouble() * Mathf.PI * 2f;
                var center = new Vector3(Mathf.Cos(angle) * radius, 0f, Mathf.Sin(angle) * radius);
                center.y = SampleHeight(terrain, center) + 0.12f;
                var scale = Mathf.Lerp(0.25f, 0.85f, (float)random.NextDouble());
                var start = vertices.Count;
                vertices.Add(center + Vector3.up * scale);
                vertices.Add(center + Vector3.right * scale);
                vertices.Add(center + Vector3.forward * scale * 0.72f);
                vertices.Add(center - Vector3.right * scale * 0.86f);
                vertices.Add(center - Vector3.forward * scale * 0.75f);
                vertices.Add(center - Vector3.up * scale * 0.18f);
                AddOctahedronTriangles(triangles, start);
            }

            var mesh = new Mesh { name = "Combined field stones" };
            mesh.SetVertices(vertices);
            mesh.SetTriangles(triangles, 0);
            mesh.RecalculateNormals();
            mesh.RecalculateBounds();
            var gameObject = new GameObject("Scattered field stones");
            gameObject.transform.SetParent(parent, false);
            gameObject.AddComponent<MeshFilter>().sharedMesh = mesh;
            gameObject.AddComponent<MeshRenderer>().sharedMaterial = material;
            gameObject.isStatic = true;
        }

        static void AddOctahedronTriangles(List<int> triangles, int start)
        {
            var faces = new[]
            {
                0, 2, 1, 0, 3, 2, 0, 4, 3, 0, 1, 4,
                5, 1, 2, 5, 2, 3, 5, 3, 4, 5, 4, 1
            };
            foreach (var index in faces)
                triangles.Add(start + index);
        }

        static void CreateWell(Transform parent, Terrain terrain, Material stone, Material wood, Material iron)
        {
            var center = new Vector3(-10.5f, 0f, 1.5f);
            center.y = SampleHeight(terrain, center);
            var root = new GameObject("Village stone well").transform;
            root.SetParent(parent, false);
            root.position = center;
            for (var i = 0; i < 12; i++)
            {
                var angle = i / 12f * Mathf.PI * 2f;
                var block = Primitive(root, "Worn well stone", PrimitiveType.Cube,
                    new Vector3(Mathf.Cos(angle) * 1.55f, 0.48f, Mathf.Sin(angle) * 1.55f),
                    new Vector3(0.92f, 0.62f, 0.72f), stone, false);
                block.transform.rotation = Quaternion.Euler(0f, -angle * Mathf.Rad2Deg, 0f);
            }
            Primitive(root, "Well post left", PrimitiveType.Cube, new Vector3(-1.45f, 2.25f, 0f), new Vector3(0.24f, 3.5f, 0.24f), wood, false);
            Primitive(root, "Well post right", PrimitiveType.Cube, new Vector3(1.45f, 2.25f, 0f), new Vector3(0.24f, 3.5f, 0.24f), wood, false);
            Primitive(root, "Well cross beam", PrimitiveType.Cube, new Vector3(0f, 3.75f, 0f), new Vector3(3.4f, 0.26f, 0.30f), wood, false);
            var spindle = Primitive(root, "Iron spindle", PrimitiveType.Cylinder, new Vector3(0f, 2.35f, 0f), new Vector3(0.16f, 1.4f, 0.16f), iron, false);
            spindle.transform.rotation = Quaternion.Euler(0f, 0f, 90f);
        }

        static void CreateMarketProps(Transform parent, Terrain terrain, Material darkWood, Material wood, Material cloth)
        {
            var root = new GameObject("Market props").transform;
            root.SetParent(parent, false);
            var anchor = new Vector3(-1.5f, SampleHeight(terrain, new Vector3(-1.5f, 0f, 7f)), 7f);
            root.position = anchor;
            for (var i = 0; i < 3; i++)
            {
                var crate = Primitive(root, "Rough supply crate", PrimitiveType.Cube,
                    new Vector3(i * 1.2f, 0.48f + (i % 2) * 0.25f, (i % 2) * 1.05f),
                    new Vector3(1.0f, 0.9f, 1.0f), wood, false);
                crate.transform.rotation = Quaternion.Euler(0f, i * 17f - 12f, 0f);
            }
            Primitive(root, "Market trestle", PrimitiveType.Cube, new Vector3(-2.8f, 1.05f, -0.3f), new Vector3(3.8f, 0.18f, 1.35f), darkWood, false);
            Primitive(root, "Cloth awning", PrimitiveType.Cube, new Vector3(-2.8f, 3.05f, -0.3f), new Vector3(4.2f, 0.12f, 2.4f), cloth, false);
            for (var x = -1; x <= 1; x += 2)
            for (var z = -1; z <= 1; z += 2)
                Primitive(root, "Awning pole", PrimitiveType.Cube, new Vector3(-2.8f + x * 1.8f, 1.65f, -0.3f + z * 0.9f), new Vector3(0.12f, 3.2f, 0.12f), darkWood, false);
        }

        static void CreateFenceRun(
            Transform parent,
            Terrain terrain,
            Material material,
            Vector3 start,
            Vector3 direction,
            int segments,
            float spacing)
        {
            var root = new GameObject("Split oak fence").transform;
            root.SetParent(parent, false);
            direction.Normalize();
            for (var i = 0; i <= segments; i++)
            {
                var point = start + direction * (i * spacing);
                point.y = SampleHeight(terrain, point);
                Primitive(root, "Fence post", PrimitiveType.Cube, point + Vector3.up * 0.72f,
                    new Vector3(0.18f, 1.45f, 0.18f), material, false);
                if (i == segments)
                    continue;
                var middle = point + direction * (spacing * 0.5f) + Vector3.up * 0.8f;
                var rail = Primitive(root, "Fence rail", PrimitiveType.Cube, middle,
                    new Vector3(0.13f, 0.13f, spacing + 0.18f), material, false);
                rail.transform.rotation = Quaternion.LookRotation(direction, Vector3.up);
            }
        }

        static void CreateCampfire(Transform parent, Terrain terrain, Material baseMaterial, Material stone, Material wood)
        {
            var center = new Vector3(4.5f, 0f, 4.5f);
            center.y = SampleHeight(terrain, center);
            var root = new GameObject("Village campfire").transform;
            root.SetParent(parent, false);
            root.position = center;
            for (var i = 0; i < 9; i++)
            {
                var angle = i / 9f * Mathf.PI * 2f;
                Primitive(root, "Fire ring stone", PrimitiveType.Sphere,
                    new Vector3(Mathf.Cos(angle) * 0.82f, 0.16f, Mathf.Sin(angle) * 0.82f),
                    new Vector3(0.38f, 0.26f, 0.34f), stone, false);
            }
            var logA = Primitive(root, "Firewood", PrimitiveType.Cylinder, new Vector3(0f, 0.26f, 0f), new Vector3(0.20f, 0.78f, 0.20f), wood, false);
            logA.transform.rotation = Quaternion.Euler(90f, 35f, 0f);
            var logB = Primitive(root, "Firewood", PrimitiveType.Cylinder, new Vector3(0f, 0.28f, 0f), new Vector3(0.20f, 0.78f, 0.20f), wood, false);
            logB.transform.rotation = Quaternion.Euler(90f, -55f, 0f);

            var fireMaterial = MakeMaterial(baseMaterial, "Fire glow", new Color(1f, 0.20f, 0.015f));
            fireMaterial.EnableKeyword("_EMISSION");
            fireMaterial.SetColor("_EmissionColor", new Color(3.2f, 0.45f, 0.025f));
            var particles = new GameObject("Fire embers");
            particles.transform.SetParent(root, false);
            particles.transform.localPosition = new Vector3(0f, 0.38f, 0f);
            var system = particles.AddComponent<ParticleSystem>();
            var main = system.main;
            main.loop = true;
            main.startLifetime = new ParticleSystem.MinMaxCurve(0.45f, 0.95f);
            main.startSpeed = new ParticleSystem.MinMaxCurve(0.55f, 1.35f);
            main.startSize = new ParticleSystem.MinMaxCurve(0.08f, 0.22f);
            main.startColor = new ParticleSystem.MinMaxGradient(new Color(1f, 0.18f, 0.01f), new Color(1f, 0.72f, 0.08f));
            main.maxParticles = 48;
            main.simulationSpace = ParticleSystemSimulationSpace.World;
            var emission = system.emission;
            emission.rateOverTime = 18f;
            var shape = system.shape;
            shape.shapeType = ParticleSystemShapeType.Cone;
            shape.angle = 16f;
            shape.radius = 0.34f;
            particles.GetComponent<ParticleSystemRenderer>().sharedMaterial = fireMaterial;

            var lightObject = new GameObject("Fire light");
            lightObject.transform.SetParent(root, false);
            lightObject.transform.localPosition = new Vector3(0f, 1.1f, 0f);
            var light = lightObject.AddComponent<Light>();
            light.type = LightType.Point;
            light.color = new Color(1f, 0.40f, 0.10f);
            light.intensity = 1.8f;
            light.range = 8f;
            light.shadows = LightShadows.None;
            lightObject.AddComponent<FirelightFlicker>();
        }

        static void CreateWindAndMotes(Transform parent, Material baseMaterial)
        {
            var windObject = new GameObject("Highland wind");
            windObject.transform.SetParent(parent, false);
            windObject.transform.rotation = Quaternion.Euler(12f, 35f, 0f);
            var wind = windObject.AddComponent<WindZone>();
            wind.mode = WindZoneMode.Directional;
            wind.windMain = 0.42f;
            wind.windTurbulence = 0.28f;
            wind.windPulseMagnitude = 0.22f;
            wind.windPulseFrequency = 0.14f;

            var moteMaterial = MakeMaterial(baseMaterial, "Sunlit pollen", new Color(0.95f, 0.70f, 0.18f, 0.55f));
            SetTransparent(moteMaterial);
            moteMaterial.EnableKeyword("_EMISSION");
            moteMaterial.SetColor("_EmissionColor", new Color(0.8f, 0.38f, 0.035f));
            var motes = new GameObject("Sunlit drifting motes");
            motes.transform.SetParent(parent, false);
            motes.transform.position = new Vector3(0f, 5f, 0f);
            var particles = motes.AddComponent<ParticleSystem>();
            var main = particles.main;
            main.loop = true;
            main.startLifetime = new ParticleSystem.MinMaxCurve(9f, 16f);
            main.startSpeed = new ParticleSystem.MinMaxCurve(0.25f, 0.65f);
            main.startSize = new ParticleSystem.MinMaxCurve(0.035f, 0.095f);
            main.startColor = new ParticleSystem.MinMaxGradient(new Color(1f, 0.68f, 0.18f, 0.18f), new Color(1f, 0.86f, 0.38f, 0.55f));
            main.maxParticles = 180;
            main.simulationSpace = ParticleSystemSimulationSpace.World;
            var emission = particles.emission;
            emission.rateOverTime = 8f;
            var shape = particles.shape;
            shape.shapeType = ParticleSystemShapeType.Box;
            shape.scale = new Vector3(110f, 8f, 110f);
            var velocity = particles.velocityOverLifetime;
            velocity.enabled = true;
            velocity.x = new ParticleSystem.MinMaxCurve(0.3f, 0.9f);
            velocity.y = new ParticleSystem.MinMaxCurve(0f, 0f);
            velocity.z = new ParticleSystem.MinMaxCurve(0.05f, 0.35f);
            motes.GetComponent<ParticleSystemRenderer>().sharedMaterial = moteMaterial;
        }

        static GameObject Primitive(
            Transform parent,
            string label,
            PrimitiveType type,
            Vector3 position,
            Vector3 scale,
            Material material,
            bool keepCollider)
        {
            var result = GameObject.CreatePrimitive(type);
            result.name = label;
            result.transform.SetParent(parent, false);
            result.transform.localPosition = position;
            result.transform.localScale = scale;
            result.GetComponent<Renderer>().sharedMaterial = material;
            var collider = result.GetComponent<Collider>();
            if (collider != null)
                collider.enabled = keepCollider;
            result.isStatic = true;
            return result;
        }

        static Material MakeMaterial(Material baseMaterial, string label, Color color)
        {
            var material = new Material(baseMaterial) { name = "Runtime " + label, color = color };
            material.enableInstancing = true;
            return material;
        }

        static void SetTransparent(Material material)
        {
            material.SetFloat("_Surface", 1f);
            material.SetFloat("_Blend", 0f);
            material.SetFloat("_SrcBlend", (float)BlendMode.SrcAlpha);
            material.SetFloat("_DstBlend", (float)BlendMode.OneMinusSrcAlpha);
            material.SetFloat("_ZWrite", 0f);
            material.EnableKeyword("_SURFACE_TYPE_TRANSPARENT");
            material.renderQueue = 3000;
        }

        static float SampleHeight(Terrain terrain, Vector3 position)
        {
            return terrain != null
                ? terrain.SampleHeight(position) + terrain.transform.position.y
                : position.y;
        }
    }

    public sealed class FirelightFlicker : MonoBehaviour
    {
        Light source;

        void Awake() => source = GetComponent<Light>();

        void Update()
        {
            if (source == null)
                return;
            source.intensity = 1.62f + Mathf.PerlinNoise(Time.unscaledTime * 5.2f, 3.7f) * 0.48f;
        }
    }

    public sealed class LumberCampVisual : MonoBehaviour
    {
        Transform timber;
        int initialTimber;

        void Awake()
        {
            timber = transform.Find("Timber reserve visual");
            initialTimber = BuildingCatalog.LoadDefault()
                .Get(BuildingArchetype.LumberCamp).initialResource;
        }

        public void Refresh(int remainingTimber, int workers)
        {
            if (timber == null)
                timber = transform.Find("Timber reserve visual");
            if (timber != null)
            {
                var amount = Mathf.Clamp01(remainingTimber / (float)initialTimber);
                timber.localScale = new Vector3(1f, Mathf.Lerp(0.12f, 1f, amount), 1f);
                timber.gameObject.SetActive(true);
            }
            transform.localScale = workers > 0 ? Vector3.one : new Vector3(0.98f, 0.98f, 0.98f);
        }
    }
}
