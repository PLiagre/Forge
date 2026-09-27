using UnityEngine;
using UnityEngine.InputSystem;
using UnityEngine.SceneManagement;

namespace ForgeLocal3D
{
    // Ambiance artistique du ksar : heure, vent de sable, lanternes. Aucune donnée de simulation.
    [ExecuteAlways] public sealed class DesertEnvironment : MonoBehaviour
    {
        [System.Serializable] public class Viewpoint
        {
            public string name;public Vector3 position,target;public float fieldOfView;
        }
        public Viewpoint[] viewpoints;
        public string village; public int seed;
        public string[] scenes,labels;
        public Light sun; public Light[] fires;
        public Camera view; public Material sky;
        public ParticleSystem sand,veil; public ParticleSystem[] smoke,flames;
        public int weather=0;
        public float hour=17f;
        public bool showPanel=true;
        static readonly string[] States={"Plein soleil","Vent de sable","Brume de chaleur"};
        void OnEnable(){Apply();}
        void Update()
        {
            if(!Application.isPlaying){Apply();return;}
            var k=Keyboard.current;
            if(k!=null)
            {
                if(k.hKey.wasPressedThisFrame)showPanel=!showPanel;
                var walking=FindFirstObjectByType<CitadelTraversal>();
                if(walking && walking.walking)
                {
                    if(k.f1Key.wasPressedThisFrame && scenes.Length>0)SceneManager.LoadScene(scenes[0]);
                    if(k.f2Key.wasPressedThisFrame && scenes.Length>1)SceneManager.LoadScene(scenes[1]);
                }
                if(k.f3Key.wasPressedThisFrame)ShowView("Passage");
                if(k.f4Key.wasPressedThisFrame)ShowView("Parvis");
                if(k.f5Key.wasPressedThisFrame)ShowView("Mosquee");
                if(k.f6Key.wasPressedThisFrame)ShowView("Ilots");
                if(k.f7Key.wasPressedThisFrame)ShowView("Oasis");
                if(k.f8Key.wasPressedThisFrame)ShowView("Palmeraie");
                if(k.f9Key.wasPressedThisFrame)ShowView("Souk");
                if(k.fKey.wasPressedThisFrame && view)
                {FindFirstObjectByType<CitadelTraversal>()?.Leave();view.fieldOfView=26.4f;view.GetComponent<VillageV2Visit>().minPitch=5;}
            }
            Apply();
            for(int i=0;i<fires.Length;i++)if(fires[i])fires[i].intensity=Lantern()*(1+Mathf.Sin(Time.time*7+i)*.12f+Mathf.Sin(Time.time*13+i*2)*.07f);
        }
        float Night()=>Mathf.InverseLerp(18.2f,21f,hour);
        float Dusk()=>Mathf.Clamp01(1-Mathf.Abs(hour-18.6f)/2.2f);
        float Lantern()=>Mathf.Lerp(.9f,3.2f,Mathf.InverseLerp(17.5f,20f,hour));
        public void ShowView(string name)
        {
            if(viewpoints==null||!view)return;
            foreach(var point in viewpoints)if(point.name==name)
            {
                FindFirstObjectByType<CitadelTraversal>()?.Leave();
                view.transform.position=point.position;view.transform.LookAt(point.target);view.fieldOfView=point.fieldOfView;
                var visit=view.GetComponent<VillageV2Visit>();visit.focus=point.target;
                visit.distance=Vector3.Distance(point.position,point.target);visit.yaw=view.transform.eulerAngles.y;
                visit.pitch=Mathf.DeltaAngle(0,view.transform.eulerAngles.x);visit.minPitch=-75;
                return;
            }
        }
        public void Apply()
        {
            if(!sun||!view)return;
            float night=Night(),dusk=Dusk(),storm=weather==1?1:0,haze=weather==2?1:0;
            // Le soleil descend vers l'ouest-sud-ouest ; sa lumière rougit en s'approchant de l'horizon.
            float elevation=Mathf.Lerp(52,-4,Mathf.InverseLerp(13,19.2f,hour));
            sun.transform.rotation=Quaternion.Euler(Mathf.Max(2,elevation),-128,0);
            Color day=new Color(1,.91f,.76f),low=new Color(1,.58f,.30f),moon=new Color(.45f,.55f,.85f);
            sun.color=Color.Lerp(Color.Lerp(day,low,dusk),moon,night);
            sun.intensity=Mathf.Lerp(Mathf.Lerp(2.6f,1.7f,dusk)*(1-storm*.45f),.12f,night);
            Shader.SetGlobalColor("_AlpineAmbient",Color.Lerp(Color.Lerp(new Color(.36f,.34f,.36f),new Color(.40f,.28f,.24f),dusk),new Color(.05f,.07f,.13f),night));
            Shader.SetGlobalFloat("_AlpineDaylight",0);
            Shader.SetGlobalFloat("_AlpineNight",.35f+night*1.1f);
            Shader.SetGlobalFloat("_AlpineSnow",0);
            Shader.SetGlobalFloat("_AlpineWet",0);
            Shader.SetGlobalFloat("_AlpineWind",storm>0?1.8f:.55f);
            RenderSettings.ambientMode=UnityEngine.Rendering.AmbientMode.Trilight;
            RenderSettings.ambientSkyColor=Color.Lerp(new Color(.42f,.52f,.66f),new Color(.07f,.09f,.16f),night);
            RenderSettings.ambientEquatorColor=Color.Lerp(new Color(.52f,.42f,.32f),new Color(.06f,.06f,.09f),night);
            RenderSettings.ambientGroundColor=Color.Lerp(new Color(.42f,.30f,.20f),new Color(.04f,.035f,.04f),night);
            RenderSettings.fog=true;RenderSettings.fogMode=FogMode.Linear;
            RenderSettings.fogStartDistance=storm>0?45:haze>0?120:260;RenderSettings.fogEndDistance=storm>0?620:haze>0?700:1500;
            Color dust=Color.Lerp(new Color(.82f,.68f,.52f),new Color(.86f,.55f,.36f),dusk);
            RenderSettings.fogColor=Color.Lerp(storm>0?new Color(.78f,.58f,.38f):dust,new Color(.06f,.07f,.12f),night);
            RenderSettings.skybox=sky;view.clearFlags=CameraClearFlags.Skybox;
            if(sky){sky.SetFloat("_Night",night);sky.SetFloat("_Dusk",dusk);sky.SetFloat("_Dust",Mathf.Max(storm,haze*.45f));sky.SetVector("_SunDirection",-sun.transform.forward);}
            if(sand){var e=sand.emission;e.rateOverTime=storm*2400;if(!sand.isPlaying)sand.Play();}
            if(veil){var e=veil.emission;e.rateOverTime=storm*40+haze*8;if(!veil.isPlaying)veil.Play();}
        }
        void OnGUI()
        {
            if(!showPanel)return;
            GUI.color=new Color(.10f,.07f,.05f,.92f);GUI.DrawTexture(new Rect(22,22,335,235),Texture2D.whiteTexture);GUI.color=new Color(.96f,.86f,.68f);
            GUI.Label(new Rect(40,36,290,25),"FORGE  /  KSAR DU DÉSERT");
            GUI.Label(new Rect(38,62,310,34),village,new GUIStyle(GUI.skin.label){fontSize=23,fontStyle=FontStyle.Bold});
            GUI.Label(new Rect(40,102,305,25),"1400 · Saharien imaginaire · Graine "+seed);
            GUI.Label(new Rect(40,136,305,22),"Lumière : "+hour.ToString("0.0")+" h");
            hour=GUI.HorizontalSlider(new Rect(40,165,294,18),hour,12,22);
            for(int i=0;i<3;i++)if(GUI.Toggle(new Rect(35+i*103,199,102,27),weather==i,States[i],"Button"))weather=i;
            for(int i=0;i<scenes.Length;i++)if(GUI.Button(new Rect(22+i*208,271,202,30),"F"+(i+1)+" · "+labels[i]))SceneManager.LoadScene(scenes[i]);
            if(GUI.Button(new Rect(22,310,132,28),"F3 · Sur le pont"))ShowView("Passage");
            if(GUI.Button(new Rect(162,310,132,28),"F4 · Parvis"))ShowView("Parvis");
            if(GUI.Button(new Rect(302,310,132,28),"F5 · Mosquée"))ShowView("Mosquee");
            if(GUI.Button(new Rect(22,348,202,30),"TAB · Marcher dans la scène")){var walk=FindFirstObjectByType<CitadelTraversal>();if(walk.walking)walk.Leave();else walk.Enter();}
            if(GUI.Button(new Rect(234,348,132,30),"F7 · Oasis"))ShowView("Oasis");
            if(GUI.Button(new Rect(376,348,132,30),"F8 · Palmeraie"))ShowView("Palmeraie");
            if(GUI.Button(new Rect(22,386,202,30),"F6 · Maisons et ruelles"))ShowView("Ilots");
            if(GUI.Button(new Rect(234,386,132,30),"F9 · Souk"))ShowView("Souk");
            if(GUI.Button(new Rect(376,386,132,30),"Vue d'ensemble"))ShowView("Ksar");
            var walker=FindFirstObjectByType<CitadelTraversal>();
            if(walker && !walker.walking)GUI.Label(new Rect(24,Screen.height-34,Screen.width-45,25),"Flèches : déplacement · Clic droit : orbite · Molette : zoom · F : vue générale · H : masquer");
        }
    }
}
