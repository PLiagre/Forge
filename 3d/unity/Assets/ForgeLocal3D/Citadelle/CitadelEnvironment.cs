using UnityEngine;
using UnityEngine.InputSystem;
using UnityEngine.SceneManagement;

namespace ForgeLocal3D
{
    // Ambiance artistique : aucune donnée de simulation n'est modifiée.
    [ExecuteAlways] public sealed class CitadelEnvironment : MonoBehaviour
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
        public ParticleSystem snow; public ParticleSystem[] smoke,flames;
        public int weather=0;
        public float hour=15.5f;
        public bool showPanel=true;
        static readonly string[] States={"Éclaircie froide","Neige et vent","Brouillard"};
        void OnEnable(){Apply();}
        void Update()
        {
            if(!Application.isPlaying){Apply();return;}
            if(Keyboard.current!=null && Keyboard.current.hKey.wasPressedThisFrame)showPanel=!showPanel;
            if(Keyboard.current!=null)
            {
                var walking=FindFirstObjectByType<CitadelTraversal>();
                if(walking && walking.walking)
                {
                    if(Keyboard.current.f1Key.wasPressedThisFrame && scenes.Length>0)SceneManager.LoadScene(scenes[0]);
                    if(Keyboard.current.f2Key.wasPressedThisFrame && scenes.Length>1)SceneManager.LoadScene(scenes[1]);
                }
                if(Keyboard.current.f3Key.wasPressedThisFrame)ShowView("Passage");
                if(Keyboard.current.f4Key.wasPressedThisFrame)ShowView("Parvis");
                if(Keyboard.current.f5Key.wasPressedThisFrame)ShowView("Cathedrale");
                if(Keyboard.current.f6Key.wasPressedThisFrame)ShowView("Ilots");
                if(Keyboard.current.f7Key.wasPressedThisFrame)ShowView("Forge");
                if(Keyboard.current.f9Key.wasPressedThisFrame)ShowView("Marche");
                if(Keyboard.current.f8Key.wasPressedThisFrame)ShowView("Habitat");
                if(Keyboard.current.fKey.wasPressedThisFrame && view)
                {FindFirstObjectByType<CitadelTraversal>()?.Leave();view.fieldOfView=26.4f;view.GetComponent<VillageV2Visit>().minPitch=5;}
            }
            Apply();
            for(int i=0;i<fires.Length;i++)if(fires[i])fires[i].intensity=2.6f+Mathf.Sin(Time.time*9+i)*.45f+Mathf.Sin(Time.time*17+i*2)*.28f;
        }
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
            float night=Mathf.InverseLerp(16.5f,21,hour);
            Shader.SetGlobalColor("_AlpineAmbient",Color.Lerp(new Color(.30f,.35f,.41f),new Color(.055f,.085f,.14f),night));
            Shader.SetGlobalFloat("_AlpineDaylight",0);
            Shader.SetGlobalFloat("_AlpineNight",.8f+night*.4f);
            Shader.SetGlobalFloat("_AlpineSnow",0);
            Shader.SetGlobalFloat("_AlpineWet",.25f);
            Shader.SetGlobalFloat("_AlpineWind",weather==1?1.6f:.65f);
            sun.transform.rotation=Quaternion.Euler(28,-125,0);
            sun.color=Color.Lerp(weather==0?new Color(1,.88f,.73f):new Color(.84f,.89f,1),new Color(.55f,.66f,.9f),night);
            sun.intensity=Mathf.Lerp(weather==0?2.35f:1.55f,.18f,night);
            RenderSettings.ambientMode=UnityEngine.Rendering.AmbientMode.Trilight;
            RenderSettings.ambientSkyColor=new Color(.24f,.30f,.36f);RenderSettings.ambientEquatorColor=new Color(.17f,.22f,.28f);RenderSettings.ambientGroundColor=new Color(.08f,.11f,.16f);
            RenderSettings.fog=true;RenderSettings.fogMode=FogMode.Linear;
            RenderSettings.fogStartDistance=weather==2?110:190;RenderSettings.fogEndDistance=weather==2?560:850;
            RenderSettings.fogColor=Color.Lerp(new Color(.34f,.41f,.47f),new Color(.055f,.09f,.15f),night);
            RenderSettings.skybox=sky;view.clearFlags=CameraClearFlags.Skybox;
            if(sky)sky.SetFloat("_Night",night);
            if(snow){var e=snow.emission;e.rateOverTime=weather==1?340:0;if(!snow.isPlaying)snow.Play();}
        }
        void OnGUI()
        {
            if(!showPanel)return;
            GUI.color=new Color(.035f,.045f,.065f,.94f);GUI.DrawTexture(new Rect(22,22,335,235),Texture2D.whiteTexture);GUI.color=new Color(.91f,.86f,.73f);
            GUI.Label(new Rect(40,36,290,25),"FORGE  /  CITADELLE ALPINE");
            GUI.Label(new Rect(38,62,310,34),village,new GUIStyle(GUI.skin.label){fontSize=23,fontStyle=FontStyle.Bold});
            GUI.Label(new Rect(40,102,305,25),"1400 · Gothique alpin imaginaire · Graine "+seed);
            GUI.Label(new Rect(40,136,305,22),"Lumière : "+hour.ToString("0.0")+" h");
            hour=GUI.HorizontalSlider(new Rect(40,165,294,18),hour,12,22);
            for(int i=0;i<3;i++)if(GUI.Toggle(new Rect(35+i*103,199,102,27),weather==i,States[i],"Button"))weather=i;
            for(int i=0;i<scenes.Length;i++)if(GUI.Button(new Rect(22+i*208,271,202,30),"F"+(i+1)+" · "+labels[i]))SceneManager.LoadScene(scenes[i]);
            if(GUI.Button(new Rect(22,310,132,28),"F3 · Sur le pont"))ShowView("Passage");
            if(GUI.Button(new Rect(162,310,132,28),"F4 · Parvis"))ShowView("Parvis");
            if(GUI.Button(new Rect(302,310,132,28),"F5 · Cathédrale"))ShowView("Cathedrale");
            if(GUI.Button(new Rect(22,348,202,30),"TAB · Marcher dans la scène")){var walk=FindFirstObjectByType<CitadelTraversal>();if(walk.walking)walk.Leave();else walk.Enter();}
            if(GUI.Button(new Rect(234,348,132,30),"Village et accès"))ShowView("Vallee");
            if(GUI.Button(new Rect(376,348,132,30),"Forêt"))ShowView("Foret");
            if(GUI.Button(new Rect(22,386,202,30),"F6 · Maisons et ruelles"))ShowView("Ilots");
            if(GUI.Button(new Rect(234,386,132,28),"F7 · Forge"))ShowView("Forge");
            if(GUI.Button(new Rect(22,424,202,30),"B · Construire une habitation"))FindFirstObjectByType<CitadelConstruction>()?.Toggle();
            if(GUI.Button(new Rect(234,424,132,30),"F8 · Colombages"))ShowView("Habitat");
            if(GUI.Button(new Rect(376,424,132,30),"F9 · Marché"))ShowView("Marche");
            if(!FindFirstObjectByType<CitadelTraversal>().walking)GUI.Label(new Rect(24,Screen.height-34,Screen.width-45,25),"Flèches : déplacement · Clic droit : orbite · Molette : zoom · F : vue générale · H : masquer");
        }
    }
}
