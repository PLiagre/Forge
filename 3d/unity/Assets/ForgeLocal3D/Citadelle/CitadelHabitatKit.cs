using System;
using UnityEngine;

namespace ForgeLocal3D
{
    // Catalogue partagé par les maisons existantes et le chantier du joueur.
    public sealed class CitadelHabitatKit : ScriptableObject
    {
        [Serializable] public class Module
        {
            public string id,label,kind; public GameObject prefab; public Vector3 size;
        }
        public Module[] modules; public GameObject[] houses; public Material gridMaterial;
        public float grid=1.5f,storey=3;
    }
}
