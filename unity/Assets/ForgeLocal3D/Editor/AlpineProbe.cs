using System;
using System.IO;
using System.Linq;
using UnityEditor;
using UnityEngine;
namespace ForgeLocal3D
{
    public static class AlpineProbe
    {
        [Serializable] public class Points { public Vector3[] points; }
        public static void Check()
        {
            var model = AssetDatabase.LoadAssetAtPath<GameObject>("Assets/ForgeLocal3D/V2/Landscapes/hautes_roches.fbx");
            var go = UnityEngine.Object.Instantiate(model);
            var filter = go.GetComponentsInChildren<MeshFilter>().First(f => f.name.StartsWith("Terrain"));
            var points = filter.sharedMesh.vertices.Where((v, i) => i % 53 == 0).Select(filter.transform.TransformPoint).ToArray();
            Directory.CreateDirectory("../local3d/alpin");
            File.WriteAllText("../local3d/alpin/axes-unity.json", JsonUtility.ToJson(new Points { points = points }));
            UnityEngine.Object.DestroyImmediate(go);
            Debug.Log("PROBE_OK " + points.Length);
        }
    }
}
