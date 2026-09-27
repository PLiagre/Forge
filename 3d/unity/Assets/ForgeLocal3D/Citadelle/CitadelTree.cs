using UnityEngine;

namespace ForgeLocal3D
{
    // Essai local d'exploitation de la forêt : l'arbre tombe depuis son pivot conservé.
    public sealed class CitadelTree : MonoBehaviour
    {
        public bool felled; public bool landed;
        Quaternion initial,target;float elapsed;
        void Start(){if(!felled)enabled=false;}
        public void Fell(Vector3 from)
        {
            if(felled)return;
            enabled=true;felled=true;initial=transform.rotation;
            Vector3 direction=transform.position-from;direction.y=0;
            if(direction.sqrMagnitude<.01f)direction=Vector3.forward;
            target=Quaternion.AngleAxis(88,Vector3.Cross(Vector3.up,direction.normalized))*initial;
            GetComponent<CapsuleCollider>().enabled=false;
        }
        void Update()
        {
            if(!felled||landed)return;
            elapsed+=Time.deltaTime;float t=Mathf.Clamp01(elapsed/2.2f);
            transform.rotation=Quaternion.Slerp(initial,target,t*t);
            if(t>=1){landed=true;enabled=false;}
        }
    }
}
