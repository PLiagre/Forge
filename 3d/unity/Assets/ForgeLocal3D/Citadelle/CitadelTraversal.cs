using System;
using UnityEngine;
using UnityEngine.InputSystem;

namespace ForgeLocal3D
{
    // Déplacement sur les collisions de la scène ; aucun état du monde historique.
    public sealed class CitadelTraversal : MonoBehaviour
    {
        [Serializable] public class Route { public string id; public float width; public Vector3[] points; }
        [Serializable] public class Plot { public string id; public Vector3 position; public Vector2 size; }
        public Route[] routes; public Plot[] plots;
        public Vector3 spawn,forest; public Camera view;
        public bool walking,automatic;
        public CharacterController body;
        Vector3 savedPosition; Quaternion savedRotation; float savedFov,yaw,pitch,vertical;
        Transform savedParent; bool savedOrbit;
        public void Enter()
        {
            if(walking)return;
            savedParent=view.transform.parent;savedPosition=view.transform.position;savedRotation=view.transform.rotation;savedFov=view.fieldOfView;
            var orbit=view.GetComponent<VillageV2Visit>();savedOrbit=orbit.enabled;orbit.enabled=false;
            body.enabled=false;transform.position=spawn;body.enabled=true;
            view.transform.SetParent(transform);view.transform.localPosition=new Vector3(0,1.7f,0);
            yaw=0;pitch=0;vertical=0;view.fieldOfView=65;view.nearClipPlane=.08f;walking=true;Look();
        }
        public void Leave()
        {
            if(!walking)return;
            walking=false;body.enabled=false;view.transform.SetParent(savedParent);
            view.transform.SetPositionAndRotation(savedPosition,savedRotation);view.fieldOfView=savedFov;view.nearClipPlane=.3f;
            view.GetComponent<VillageV2Visit>().enabled=savedOrbit;
        }
        void Look()=>view.transform.rotation=Quaternion.Euler(pitch,yaw,0);
        public void Step(Vector3 horizontal,float seconds)
        {
            if(!walking)return;
            if(body.isGrounded && vertical<0)vertical=-2;
            vertical=Mathf.Max(-35,vertical-20*seconds);
            horizontal.y=vertical;body.Move(horizontal*seconds);
        }
        public void Face(Vector3 point)
        {
            Vector3 d=point-transform.position;d.y=0;
            if(d.sqrMagnitude>.001f){yaw=Quaternion.LookRotation(d).eulerAngles.y;pitch=0;Look();}
        }
        void Update()
        {
            var k=Keyboard.current;
            if(k!=null && k.tabKey.wasPressedThisFrame){if(walking)Leave();else Enter();}
            if(!walking||automatic)return;
            Vector2 input=Vector2.zero;
            if(k!=null)
            {
                if(k.wKey.isPressed||k.zKey.isPressed||k.upArrowKey.isPressed)input.y++;
                if(k.sKey.isPressed||k.downArrowKey.isPressed)input.y--;
                if(k.aKey.isPressed||k.qKey.isPressed||k.leftArrowKey.isPressed)input.x--;
                if(k.dKey.isPressed||k.rightArrowKey.isPressed)input.x++;
            }
            var mouse=Mouse.current;
            if(mouse!=null && mouse.rightButton.isPressed)
            {var delta=mouse.delta.ReadValue();yaw+=delta.x*.14f;pitch=Mathf.Clamp(pitch-delta.y*.14f,-80,80);Look();}
            Vector3 motion=Quaternion.Euler(0,yaw,0)*new Vector3(input.normalized.x,0,input.normalized.y);
            Step(motion*(k!=null && k.leftShiftKey.isPressed?5:2.8f),Time.deltaTime);
            if(k!=null && k.eKey.wasPressedThisFrame)NearestTree()?.Fell(transform.position);
        }
        public CitadelTree NearestTree()
        {
            CitadelTree nearest=null;float distance=3.3f;
            foreach(var hit in Physics.OverlapSphere(transform.position+Vector3.up,3.3f))
            {
                var tree=hit.GetComponent<CitadelTree>();if(!tree||tree.felled)continue;
                float d=Vector3.Distance(transform.position,tree.transform.position);
                if(d<distance){distance=d;nearest=tree;}
            }
            return nearest;
        }
        void OnGUI()
        {
            if(!walking||automatic)return;
            var env=FindFirstObjectByType<CitadelEnvironment>();if(env && !env.showPanel)return;
            string text="TAB : vue libre · ZQSD / flèches : marcher · Maj : courir · Clic droit : regarder";
            if(NearestTree())text+="\nE : abattre ce sapin";
            foreach(var p in plots)
                if(Mathf.Abs(transform.position.x-p.position.x)<p.size.x/2 && Mathf.Abs(transform.position.z-p.position.z)<p.size.y/2)
                    text+="\n"+p.id.Replace('_',' ')+" · Clairière disponible : "+p.size.x+" × "+p.size.y+" m";
            GUI.Box(new Rect(20,Screen.height-100,700,75),text);
        }
    }
}
