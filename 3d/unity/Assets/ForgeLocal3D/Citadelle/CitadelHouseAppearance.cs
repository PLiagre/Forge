using UnityEngine;

namespace ForgeLocal3D
{
    [ExecuteAlways] public sealed class CitadelHouseAppearance : MonoBehaviour
    {
        public Color tint=Color.white;
        // Nom du matériau d'enduit à teinter ; la citadelle garde « enduit ».
        public string matter="enduit";
        void OnEnable()=>Apply();
        public void Apply()
        {
            foreach(var renderer in GetComponentsInChildren<MeshRenderer>(true))
                for(int i=0;i<renderer.sharedMaterials.Length;i++)
                    if(renderer.sharedMaterials[i].name==matter)
                    {var block=new MaterialPropertyBlock();block.SetColor("_BaseColor",tint);renderer.SetPropertyBlock(block,i);}
        }
    }
}
